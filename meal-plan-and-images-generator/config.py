import os

IMAGE_SIZES = (256, 512, 1024)
CDN_URL_PREFIX = "https://static.mealhow.ai/meal-images/"

DATASTORE_DB = os.environ.get("DATASTORE_DB", "mealhow-dev")
OPENAI_GPT_MODEL_VERSION = os.environ.get("OPENAI_GPT_MODEL_VERSION", "gpt-4-1106-preview")
DESTINATION_BUCKET = os.environ.get("DESTINATION_BUCKET", "mealhow-ai-generated-meal-images")
