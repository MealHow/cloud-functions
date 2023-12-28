import asyncio

import clients
import cloud_storage
import config
import database
from mealhow_sdk import external_api


async def save_image(image_url: str, meal_name: str):
    async with clients.http_client.session.get(image_url) as response:
        future = await database.save_new_meal_image_object(meal_name)
        await cloud_storage.upload_raw_image_on_cloud_storage(
            blob=await response.content.read(),
            meal_name=meal_name,
        )
        future.wait()


async def generate_images_for_meals(meal_plan: dict):
    snake_cased_meal_names = set()
    meal_names_map = {}
    meal_to_image_map = {}

    for day in meal_plan:
        for meal in meal_plan[day]["meals"]:
            meal_id = meal["id"].split("-")[0]
            snake_cased_meal_names.add(meal_id)
            meal_names_map[meal_id] = meal["meal_name"]

    unmatched_meal_ids = []
    for meal_id in snake_cased_meal_names:
        meal_obj = await database.get_meal_image_obj_by_key(meal_id)
        if meal_obj is None:
            unmatched_meal_ids.append(meal_id)

    async with asyncio.TaskGroup() as tg:
        for meal_id in unmatched_meal_ids:
            meal_to_image_map[meal_id] = tg.create_task(
                external_api.openai_get_generated_image_url(
                    config.MEAL_IMAGE_PROMPT.format(meal_name=meal_names_map[meal_id])
                )
            )

    tasks = [save_image(meal_to_image_map[meal_name].result(), meal_name) for meal_name in meal_to_image_map]
    for i in range(0, len(tasks), 5):
        group = tasks[i : i + 5]
        await asyncio.gather(*group)
