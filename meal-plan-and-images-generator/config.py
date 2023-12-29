import os

IMAGE_SIZES = (256, 512, 1024)
CDN_URL_PREFIX = "https://static.mealhow.ai/meal-images/"

DATASTORE_DB = os.environ.get("DATASTORE_DB", "mealhow-dev")
