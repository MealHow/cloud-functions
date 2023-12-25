from google.cloud import datastore

import clients
import config


async def get_meal_image_obj_by_key(meal_name: str):
    key = clients.datastore_client.key("MealImage", meal_name)
    return clients.datastore_client.get(key)


async def save_new_meal_image_object(meal_name_key: str, full_meal_name: str):
    key = clients.datastore_client.key("MealImage", meal_name_key)
    meal_obj = datastore.Entity(key=key)
    meal_obj.update({
        "full_name": full_meal_name,
        "images": {
            str(i): f"{config.CDN_URL_PREFIX}{meal_name_key}_{i}x{i}.jpg" for i in config.IMAGE_SIZES
        },
    })
    clients.datastore_client.put(meal_obj)
