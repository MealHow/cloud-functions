import asyncio
import base64
import json
import os

import functions_framework
import openai
from cloudevents.http.event import CloudEvent
from google.cloud import ndb
from mealhow_sdk import enums, external_api, parsers, prompt_templates
from mealhow_sdk.clients import HttpClient
from mealhow_sdk.datastore_models import Meal, ShoppingList, ShoppingListItem

OPENAI_GPT_MODEL_VERSION = os.environ["OPENAI_GPT_MODEL_VERSION"]

http_client = HttpClient()
ndb_client = ndb.Client()


async def create_shopping_list_for_meals_without_recipes(meals: list[Meal]) -> list[dict]:
    meals_list_text = "\n".join([f"- {meal.full_name} ({meal.calories} calories)" for meal in meals])

    response = await external_api.openai_get_gpt_response(
        model=OPENAI_GPT_MODEL_VERSION,
        text_request=prompt_templates.SHOPPING_LIST_MEALS_REQUEST.format(meal_plan=meals_list_text),
    )
    return await parsers.parse_shopping_list(response)


async def create_shopping_list_for_meals_with_recipes(ingredients: list[str]) -> list[dict]:
    ingredients_text_list = "\n".join([f"- {ingredient}" for ingredient in ingredients])

    response = await external_api.openai_get_gpt_response(
        model=OPENAI_GPT_MODEL_VERSION,
        text_request=prompt_templates.SHOPPING_LIST_INGREDIENTS_REQUEST.format(ingredients=ingredients_text_list),
    )
    return await parsers.parse_shopping_list(response)


async def main(input_data: dict) -> None:
    http_client.start()
    openai.aiosession.set(http_client())

    with ndb_client.context():
        shopping_list = ShoppingList.get_by_id(input_data["shopping_list_id"])
        shopping_list.status = enums.JobStatus.in_progress.name
        shopping_list_key = shopping_list.put()
        shopping_list = shopping_list_key.get()

        try:
            meal_keys = [ndb.Key(Meal, meal_id) for meal_id in input_data["meal_ids"]]
            meals = ndb.get_multi(meal_keys)
            ingredients = []
            meals_without_recipes = []

            for meal in meals:
                if meal.recipe_status == enums.JobStatus.done.name:
                    recipe = meal.recipe.get()
                    if recipe.ingredients:
                        ingredients.extend(recipe.ingredients)
                else:
                    meals_without_recipes.append(meal)

            async with asyncio.TaskGroup() as group:
                sl1 = group.create_task(create_shopping_list_for_meals_without_recipes(meals_without_recipes))
                sl2 = group.create_task(create_shopping_list_for_meals_with_recipes(ingredients))

            shopping_list.items = shopping_list.items + [
                ShoppingListItem(
                    name=item["product_name"], quantity=item["quantity"], category=item["product_category"]
                )
                for item in sl1.result() + sl2.result()
            ]
            shopping_list.put()

        except Exception as e:
            shopping_list.status = enums.JobStatus.failed.name
            shopping_list.put()
            raise e

        else:
            shopping_list.status = enums.JobStatus.done.name
            shopping_list.put()

    await http_client.stop()


@functions_framework.cloud_event
def execute(cloud_event: CloudEvent) -> None:
    input_data = json.loads(base64.b64decode(cloud_event.data["message"]["data"]))

    loop = asyncio.new_event_loop()
    task = loop.create_task(main(input_data))
    loop.run_until_complete(task)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    task = loop.create_task(
        main(
            {
                "shopping_list_id": 5069189920325632,
                "meal_ids": [
                    "greek_yogurt_parfait_with_granola_and_mixed_berries-420",
                    "bbq_chicken_with_baked_beans_and_corn-800",
                    "avocado_toast_on_wholegrain_bread_with_poached_eggs-550",
                    "almond_ricotta_with_roasted_peppers-300",
                    "cheese_quesadilla-450",
                    "chia_pudding_with_mixed_berries-420",
                    "chicken_caesar_wrap-450",
                    "fruit_salad-250",
                    "veggie_breakfast_burrito-600",
                    "shrimp_pasta_with_marinara_sauce-600",
                ],
            }
        )
    )
    loop.run_until_complete(task)
