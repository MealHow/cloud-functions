import os
import functions_framework

from io import BytesIO
from PIL import Image
from google.cloud import storage

storage_client = storage.Client()
IMAGE_SIZES = [
    (256, 256),
    (512, 512),
    (1024, 1024),
]
DESTINATION_BUCKET = os.environ["DESTINATION_BUCKET"]
DESTINATION_DIR = os.environ["DESTINATION_DIR"]


@functions_framework.cloud_event
def convert_image(cloud_event):
    data = cloud_event.data
    object_name = data["name"]
    file_name, _ = object_name.split(".")

    bucket = storage_client.bucket(data["bucket"])
    blob = bucket.get_blob(object_name)
    buff = BytesIO()
    blob.download_to_file(buff)
    buff.seek(0)
    print(f"Downloaded '{object_name}' image")

    dest_bucket = storage_client.bucket(DESTINATION_BUCKET)

    for size in IMAGE_SIZES:
        new_image_name = f"{DESTINATION_DIR}/{file_name}_{size[0]}x{size[1]}.jpg"
        print(f"Creating '{new_image_name}' image")
        img = Image.open(buff)
        rgb_img = img.convert("RGB")
        rgb_img.thumbnail(size, Image.Resampling.LANCZOS)
        img_byte_arr = BytesIO()
        rgb_img.save(img_byte_arr, format="JPEG")
        img_byte_arr.seek(0)

        dest_blob = dest_bucket.blob(new_image_name)
        dest_blob.upload_from_file(img_byte_arr, content_type="image/jpeg")
