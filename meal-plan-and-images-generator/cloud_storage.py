import io


async def upload_raw_image_on_cloud_storage(blob, meal_name, bucket):
    raw_img = io.BytesIO(blob)
    raw_img.seek(0)
    dest_blob = bucket.blob(f"{meal_name}.png")
    dest_blob.upload_from_file(raw_img, content_type="image/png")
