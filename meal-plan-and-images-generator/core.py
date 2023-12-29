import asyncio

import clients
import cloud
import config
from mealhow_sdk import external_api


async def save_image(image_url: str, meal_image_id: str, meal_obj: dict):
    async with clients.http_client.session.get(image_url) as response:
        future = await cloud.save_new_meal_info_and_image(meal_image_id, meal_obj)
        await cloud.upload_raw_image_on_cloud_storage(
            blob=await response.content.read(),
            meal_name=meal_image_id,
        )
        future.wait()


async def save_meal_info_and_generate_images(meal_plan: dict):
    meal_images_ids = set()
    meal_id_to_obj_map = {}
    meal_id_to_image_map = {}

    for day in meal_plan:
        for meal in meal_plan[day]["meals"]:
            meal_id = meal["id"].split("-")[0]
            meal_id_to_obj_map[meal_id] = meal
            meal_images_ids.add(meal_id)

    existing_meal_images = await cloud.get_meal_image_entities_by_ids(meal_images_ids)
    unmatched_meal_ids = meal_images_ids - existing_meal_images

    async with asyncio.TaskGroup() as tg:
        for meal_id in unmatched_meal_ids:
            meal_id_to_image_map[meal_id] = tg.create_task(
                external_api.openai_get_generated_image_url(
                    config.MEAL_IMAGE_PROMPT.format(meal_name=meal_id_to_obj_map[meal_id]["meal_name"])
                )
            )

    tasks = [
        save_image(meal_id_to_image_map[meal_id].result(), meal_id, meal_id_to_obj_map[meal_id])
        for meal_id in meal_id_to_image_map
    ]
    for i in range(0, len(tasks), 5):
        group = tasks[i : i + 5]
        await asyncio.gather(*group)


async def save_meal_plan(meal_plan: dict, user_id: str):
    pass
