import io

import clients
import config
from google.cloud import ndb
from google.cloud.ndb import Future
from mealhow_sdk.datastore_models import Meal, MealImage, MealImageThumbnail, MealPlan


async def upload_raw_image_on_cloud_storage(blob, meal_name):
    raw_img = io.BytesIO(blob)
    raw_img.seek(0)
    await clients.cloud_storage_session().upload(
        bucket=config.DESTINATION_BUCKET, object_name=f"{meal_name}.png", file_data=raw_img, content_type="image/png"
    )


async def get_meal_image_entities_by_ids(meal_name_ids: set[str]) -> set:
    with clients.ndb_client.context():
        keys = [ndb.Key(MealImage, meal_id) for meal_id in meal_name_ids]
        return set(i.key.id() for i in ndb.get_multi(keys) if i is not None)


async def save_new_meal_info_and_image(meal_image_id: str, meal_obj: dict) -> Future:
    with clients.ndb_client.context():
        meal_image_key = ndb.Key(MealImage, meal_image_id)
        meal_image = MealImage(
            key=meal_image_key,
            images=[
                MealImageThumbnail(
                    size=size,
                    url=f"{config.CDN_URL_PREFIX}{meal_image_id}_{size}x{size}.jpg",
                )
                for size in config.IMAGE_SIZES
            ],
        )
        meal_image.put()

        meal_key = ndb.Key(Meal, meal_obj["id"])
        meal = Meal(
            key=meal_key,
            full_name=meal_obj["meal_name"],
            calories=int(meal_obj["calories"]),
            carbs=int(meal_obj["carbs"]),
            fats=int(meal_obj["fats"]),
            protein=int(meal_obj["protein"]),
            preparation_time=int(meal_obj["preparation_time"]),
            image=meal_image_key,
        )

        return meal.put_async()
