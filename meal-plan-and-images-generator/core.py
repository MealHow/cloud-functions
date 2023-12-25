import asyncio
from typing import Any

import clients
import cloud_storage
import config
import database
import external_api
import helpers
import parsers


async def calculate_total_daily_micronutrients(
        parsed_diet_plan: list[dict],
) -> dict[int, dict[str, int]]:
    total_daily_micronutrients = {}
    micronutrients = (
        "protein",
        "carbs",
        "fats",
        "calories",
    )

    for i in range(len(parsed_diet_plan)):
        if parsed_diet_plan[i]["day"] not in total_daily_micronutrients:
            total_daily_micronutrients[parsed_diet_plan[i]["day"]] = {
                name: 0 for name in micronutrients
            }

        for name in micronutrients:
            total_daily_micronutrients[parsed_diet_plan[i]["day"]][
                name
            ] += parsed_diet_plan[i][name]

    return total_daily_micronutrients


async def request_meal_plans(
        request_body: str, meal_plans: int = 3
) -> list[list[dict]]:
    requests = []
    parsed_meal_plans: list[Any] = []

    async with asyncio.TaskGroup() as tg:
        for _ in range(meal_plans):
            requests.append(
                tg.create_task(external_api.openai_get_gpt_response(request_body))
            )

    async with asyncio.TaskGroup() as tg:
        for req in requests:
            parsed_meal_plans.append(
                tg.create_task(parsers.parse_diet_plan(req.result()))
            )

    for i in range(len(parsed_meal_plans)):
        parsed_meal_plans[i] = parsed_meal_plans[i].result()

    return parsed_meal_plans


async def compound_most_optimal_meal_plan(
        diet_plan_variations: list[list[dict]], daily_calories_goal: int, plan_length: int = 7
) -> dict[int, dict[str, Any]]:
    daily_micronutrients = []
    optimal_meal_plan: dict[int, dict] = {}
    meal_plan_variations_structured: list[dict[int, dict]] = []

    async with asyncio.TaskGroup() as tg:
        for plan in diet_plan_variations:
            daily_micronutrients.append(
                tg.create_task(calculate_total_daily_micronutrients(plan))
            )

    for i in range(len(diet_plan_variations)):
        meal_plan: dict[int, dict[str, Any]] = {}
        for meal in diet_plan_variations[i]:
            if (day := meal["day"]) not in meal_plan:
                meal_plan[day] = {
                    "meals": [],
                    "total": daily_micronutrients[i].result()[day],
                }

            meal_plan[day]["meals"].append(meal)

        meal_plan_variations_structured.append(meal_plan)

    daily_calories_goal_diff: dict[int, int] = {
        k: 9999 for k in range(1, plan_length + 1)
    }
    for i in range(len(meal_plan_variations_structured)):
        for day in meal_plan_variations_structured[i]:
            day = int(day)
            diff = abs(
                meal_plan_variations_structured[i][day]["total"]["calories"]
                - daily_calories_goal
            )
            if diff < daily_calories_goal_diff[day]:
                optimal_meal_plan[day] = meal_plan_variations_structured[i][day]
                daily_calories_goal_diff[day] = diff

    return optimal_meal_plan


async def generate_images_for_meals(meal_plan: dict):
    snake_cased_meal_names = set()
    meal_names_map = {}
    meal_to_image_map = {}

    for day in meal_plan:
        for meal in meal_plan[day]["meals"]:
            meal_name = helpers.to_snake_case(meal["meal_name"])
            snake_cased_meal_names.add(meal_name)
            meal_names_map[meal_name] = meal["meal_name"]

    unmatched_meals = []
    for meal_name in snake_cased_meal_names:
        meal_obj = await database.get_meal_image_obj_by_key(meal_name)
        if meal_obj is None:
            unmatched_meals.append(meal_name)

    async with asyncio.TaskGroup() as tg:
        for meal_name in unmatched_meals:
            meal_to_image_map[meal_name] = tg.create_task(
                external_api.openai_get_generated_image_url(
                    config.MEAL_IMAGE_PROMPT.format(meal_name=meal_names_map[meal_name])
                )
            )

    dest_bucket = clients.storage_client.bucket(config.DESTINATION_BUCKET)

    for meal_name in meal_to_image_map:
        image_url = meal_to_image_map[meal_name].result()

        async with clients.http_client.session.get(image_url) as response:
            await cloud_storage.upload_raw_image_on_cloud_storage(
                blob=await response.content.read(),
                meal_name=meal_name,
                bucket=dest_bucket,
            )

        await database.save_new_meal_image_object(meal_name, meal_names_map[meal_name])
