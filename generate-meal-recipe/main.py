import asyncio
import base64
import json
import os

import functions_framework
import openai
from cloudevents.http.event import CloudEvent
from google.cloud import ndb
from mealhow_sdk import enums, external_api, prompt_templates, parsers
from mealhow_sdk.clients import HttpClient
from mealhow_sdk.datastore_models import Meal, MealRecipe

OPENAI_GPT_MODEL_VERSION = os.environ["OPENAI_GPT_MODEL_VERSION"]

http_client = HttpClient()
ndb_client = ndb.Client()


async def main(input_data: dict) -> None:
    http_client.start()
    openai.aiosession.set(http_client())

    with ndb_client.context():
        meal = Meal.get_by_id(input_data["meal_id"])
        try:
            response = await external_api.openai_get_gpt_response(
                model=OPENAI_GPT_MODEL_VERSION,
                text_request=prompt_templates.MEAL_RECIPE_REQUEST.format(
                    meal=f"{meal.full_name} ({meal.calories} calories)",
                ),
            )

            ingredients_content = await parsers.extract_section(response, "ngredients", "nstructions")
            if ingredients_content:
                ingredients = await parsers.extract_ingredients(ingredients_content)
                for i in range(len(ingredients)):
                    ingredients[i] = ingredients[i].strip().lower()
            else:
                ingredients = None

            recipe = MealRecipe(
                text=response,
                ingredients=ingredients,
            )
            recipe_key = recipe.put()

            meal.recipe = recipe_key
            meal.put()

        except Exception as e:
            meal.recipe_status = enums.JobStatus.failed.name
            meal.put()
            raise e

        else:
            meal.recipe_status = enums.JobStatus.done.name
            meal.put()

    await http_client.stop()


@functions_framework.cloud_event
def execute(cloud_event: CloudEvent) -> None:
    input_data = json.loads(base64.b64decode(cloud_event.data["message"]["data"]))

    loop = asyncio.new_event_loop()
    task = loop.create_task(main(input_data))
    loop.run_until_complete(task)
