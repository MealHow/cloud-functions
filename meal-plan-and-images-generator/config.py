import os

REPLACE_WORDS_MAPPING = [
    ("Monday", "1"),
    ("Tuesday", "2"),
    ("Wednesday", "3"),
    ("Thursday", "4"),
    ("Friday", "5"),
    ("Saturday", "6"),
    ("Sunday", "7"),
    ("Mon", "1"),
    ("Tue", "2"),
    ("Wed", "3"),
    ("Thu", "4"),
    ("Fri", "5"),
    ("Sat", "6"),
    ("Sun", "7"),
    ("Al1d", "Almond"),
    ("Al1ds", "Almonds"),
    ("Sal1", "Salmon"),
    ("5es", "Fries"),
    ("Le1", "Lemon"),
    ("5ed", "Fried"),
]

MEAL_PLAN_FIELDNAMES = [
    "day",
    "meal_time",
    "meal_name",
    "preparation_time",
    "calories",
    "protein",
    "carbs",
    "fats",
]
IMAGE_SIZES = (256, 512, 1024)
CDN_URL_PREFIX = "https://static.mealhow.ai/meal-images/"
MEAL_PLAN_PROMPT = """[Writing style guideline: return only meal plan in CSV format (semicolon separated): day(number); meal time; meal name; preparation time; calories; protein; carbs; fats]
Please make me a meal plan for a week's worth of meals. I must hit a {kcal}-calorie goal for each day.
"""
MEAL_IMAGE_PROMPT = """Professional food picture of {meal_name} meal on the kitchen table"""
DATASTORE_DB = os.environ["DATASTORE_DB"]
OPENAI_GPT_MODEL_VERSION = os.environ["OPENAI_GPT_MODEL_VERSION"]
DESTINATION_BUCKET = os.environ["DESTINATION_BUCKET"]
