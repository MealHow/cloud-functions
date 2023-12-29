import os

IMAGE_SIZES = (256, 512, 1024)
CDN_URL_PREFIX = "https://static.mealhow.ai/meal-images/"

DATASTORE_DB = os.environ["DATASTORE_DB"]
OPENAI_GPT_MODEL_VERSION = os.environ["OPENAI_GPT_MODEL_VERSION"]
DESTINATION_BUCKET = os.environ["DESTINATION_BUCKET"]
