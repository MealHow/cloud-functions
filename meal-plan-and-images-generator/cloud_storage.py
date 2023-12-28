import io

import config
from clients import cloud_storage_session


async def upload_raw_image_on_cloud_storage(blob, meal_name):
    raw_img = io.BytesIO(blob)
    raw_img.seek(0)
    await cloud_storage_session().upload(
        bucket=config.DESTINATION_BUCKET, object_name=f"{meal_name}.png", file_data=raw_img, content_type="image/png"
    )
