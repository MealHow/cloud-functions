import asyncio

import clients
import cloud_storage
import config
import database
from mealhow_sdk import external_api, helpers


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
