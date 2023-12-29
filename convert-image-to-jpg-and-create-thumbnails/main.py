import asyncio
import os
from io import BytesIO

import clients
import functions_framework
from mealhow_sdk.clients import CloudStorage, HttpClient
from PIL import Image

IMAGE_SIZES = [
    (256, 256),
    (512, 512),
    (1024, 1024),
]
DESTINATION_BUCKET = os.environ["DESTINATION_BUCKET"]
DESTINATION_DIR = os.environ["DESTINATION_DIR"]

cloud_storage_session = CloudStorage()
http_client = HttpClient()


async def save_image(buff: BytesIO, size: tuple[int, int], file_name: str):
    new_image_name = f"{DESTINATION_DIR}/{file_name}_{size[0]}x{size[1]}.jpg"
    img = Image.open(buff)
    rgb_img = img.convert("RGB")
    rgb_img.thumbnail(size, Image.Resampling.LANCZOS)
    img_byte_arr = BytesIO()
    rgb_img.save(img_byte_arr, format="JPEG")
    img_byte_arr.seek(0)

    await clients.cloud_storage_session().upload(
        bucket=DESTINATION_BUCKET, object_name=new_image_name, file_data=img_byte_arr, content_type="image/jpeg"
    )


async def convert_image(data):
    clients.http_client.start()
    clients.cloud_storage_session.initialise(clients.http_client())

    object_name = data["name"]
    file_name, _ = object_name.split(".")

    blob = await clients.cloud_storage_session().download(data["bucket"], object_name)
    buff = BytesIO(blob)
    buff.seek(0)

    async with asyncio.TaskGroup() as tg:
        for size in IMAGE_SIZES:
            tg.create_task(save_image(buff, size, file_name))


@functions_framework.cloud_event
def execute(cloud_event):
    data = cloud_event.data

    loop = asyncio.new_event_loop()
    task = loop.create_task(convert_image(data))
    loop.run_until_complete(task)
