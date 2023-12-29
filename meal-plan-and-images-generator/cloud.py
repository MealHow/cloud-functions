import io

import clients
import config
from google.cloud import ndb
from mealhow_sdk.datastore_models import MealImage


async def upload_raw_image_on_cloud_storage(blob, meal_name):
    raw_img = io.BytesIO(blob)
    raw_img.seek(0)
    await clients.cloud_storage_session().upload(
        bucket=config.DESTINATION_BUCKET, object_name=f"{meal_name}.png", file_data=raw_img, content_type="image/png"
    )


async def get_meal_image_obj_by_key(meal_name: str):
    with clients.ndb_client.context():
        return MealImage.get_by_id_async(meal_name).get_result()


async def save_new_meal_image_object(meal_name_key: str):
    with clients.ndb_client.context():
        key = ndb.Key(MealImage, meal_name_key)
        meal_image = MealImage(
            key=key,
            images={str(i): f"{config.CDN_URL_PREFIX}{meal_name_key}_{i}x{i}.jpg" for i in config.IMAGE_SIZES},
        )
        return meal_image.put_async()
