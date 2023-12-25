import os

MEAL_PLAN_PROMPT = """[Writing style guideline: return only meal plan in CSV format (semicolon separated): day(number); meal time; meal name; preparation time; calories; protein; carbs; fats]
Please make me a meal plan for a week's worth of meals. I must hit a {kcal}-calorie goal for each day.
"""
MEAL_IMAGE_PROMPT = """Professional food picture of {meal_name} meal on the kitchen table"""

IMAGE_SIZES = (256, 512, 1024)
CDN_URL_PREFIX = "https://static.mealhow.ai/meal-images/"

DATASTORE_DB = os.environ["DATASTORE_DB"]
OPENAI_GPT_MODEL_VERSION = os.environ["OPENAI_GPT_MODEL_VERSION"]
DESTINATION_BUCKET = os.environ["DESTINATION_BUCKET"]
