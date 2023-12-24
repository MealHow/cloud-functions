import asyncio
import csv
import os
import re
import ssl
from io import BytesIO
from typing import Any

import certifi
import functions_framework
import openai
from aiohttp import ClientSession, TCPConnector
from google.cloud import storage, datastore

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
MEAL_PLAN_REQUEST = """[Writing style guideline: return only meal plan in CSV format (semicolon separated): day(number); meal time; meal name; preparation time; calories; protein; carbs; fats]
Please make me a meal plan for a week's worth of meals. I must hit a {kcal}-calorie goal for each day.
"""

DATASTORE_DB = os.environ["DATASTORE_DB"]
OPENAI_GPT_MODEL_VERSION = os.environ["OPENAI_GPT_MODEL_VERSION"]
DESTINATION_BUCKET = os.environ["DESTINATION_BUCKET"]


class HttpClient:
    session: ClientSession | None = None

    def start(self) -> None:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        conn = TCPConnector(ssl=ssl_context)
        self.session = ClientSession(connector=conn, auto_decompress=True)

    async def stop(self) -> None:
        if self.session is None:
            return

        await self.session.close()
        self.session = None

    def __call__(self) -> ClientSession:
        assert self.session is not None
        return self.session


datastore_client = datastore.Client(database=DATASTORE_DB)
storage_client = storage.Client()
http_client = HttpClient()


async def openai_get_generated_image_url(prompt: str) -> str:
    response = await openai.Image.acreate(
        prompt=prompt,
        n=1,
        size="1024x1024",
    )
    return response["data"][0]["url"]


async def _get_chat_completion_response(prompt: str) -> str:
    response = await openai.ChatCompletion.acreate(
        model=OPENAI_GPT_MODEL_VERSION,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["choices"][0]["message"]["content"]


async def _get_text_completion_response(
        prompt: str, model: str = OPENAI_GPT_MODEL_VERSION
) -> str:
    response = await openai.Completion.acreate(
        model=model, prompt=prompt, max_tokens=1000, temperature=1
    )
    return response["choices"][0]["text"]


async def _parse_csv(
        csv_data: str, keyword: str, fieldnames: list[str], delimiter: str = ";"
) -> list[dict]:
    split_data = csv_data.splitlines()
    new_split_data = []

    while delimiter not in split_data[0]:
        split_data.pop(0)

    for i in split_data:
        if i.strip() and keyword not in i.lower():
            strip_value = i.strip()
            if strip_value.count(delimiter) == len(fieldnames) - 1:
                new_split_data.append(strip_value)
            elif (
                    strip_value.count(delimiter) + strip_value.count(",")
                    == len(fieldnames) - 1
            ):
                new_split_data.append(strip_value.replace(",", delimiter))

    csv_data = "\n".join(new_split_data)
    reader = csv.DictReader(csv_data.splitlines(), delimiter=delimiter)
    reader.fieldnames = fieldnames
    return list(reader)


async def _str_to_int(raw_data: str) -> int:
    data = raw_data.strip().split(".")[0]
    return int("".join([i for i in data if i.isdigit()]))


async def openai_get_gpt_response(
        text_request: str,
        model: str = OPENAI_GPT_MODEL_VERSION,
        max_tries_number: int = 10,
        sleep_time: int = 3,
) -> str:
    resp = ""
    is_success = False
    try_number = 0
    while not is_success and try_number < max_tries_number:
        if model == OPENAI_GPT_MODEL_VERSION:
            resp = await _get_chat_completion_response(text_request)
        else:
            resp = await _get_text_completion_response(text_request, model)

        is_success = not any(i in resp.lower() for i in ["sorry", "apologize"])
        try_number += 1
        if not is_success:
            print("Oops, something went wrong. Trying again (%s)...", try_number)
            await asyncio.sleep(sleep_time)

    return resp


async def calculate_total_daily_micronutrients(
        parsed_diet_plan: list[dict],
) -> dict[int, dict[str, int]]:
    total_daily_micronutrients = {}
    micronutrients = (
        "protein",
        "carbs",
        "fats",
        "calories",
    )

    for i in range(len(parsed_diet_plan)):
        if parsed_diet_plan[i]["day"] not in total_daily_micronutrients:
            total_daily_micronutrients[parsed_diet_plan[i]["day"]] = {
                name: 0 for name in micronutrients
            }

        for name in micronutrients:
            total_daily_micronutrients[parsed_diet_plan[i]["day"]][
                name
            ] += parsed_diet_plan[i][name]

    return total_daily_micronutrients


async def parse_diet_plan(raw_data: str) -> list[dict]:
    str_to_int_keys = (
        "day",
        "calories",
        "protein",
        "carbs",
        "fats",
        "preparation_time",
    )
    str_keys = (
        "meal_time",
        "meal_name",
    )

    for item in REPLACE_WORDS_MAPPING:
        raw_data = raw_data.replace(*item)
        raw_data = raw_data.replace(item[0].lower(), item[1])

    parsed_data = await _parse_csv(
        raw_data, keyword="preparation", fieldnames=MEAL_PLAN_FIELDNAMES
    )

    new_data = []
    for i in range(len(parsed_data)):
        try:
            for key in str_keys:
                parsed_data[i][key] = parsed_data[i][key].strip()

            for key in str_to_int_keys:
                parsed_data[i][key] = await _str_to_int(parsed_data[i][key])
        except (ValueError, AttributeError):
            pass
        else:
            new_data.append(parsed_data[i])

    return new_data


async def request_meal_plans(
        request_body: str, meal_plans: int = 3
) -> list[list[dict]]:
    requests = []
    parsed_meal_plans: list[Any] = []

    async with asyncio.TaskGroup() as tg:
        for _ in range(meal_plans):
            requests.append(
                tg.create_task(openai_get_gpt_response(request_body))
            )

    async with asyncio.TaskGroup() as tg:
        for req in requests:
            parsed_meal_plans.append(
                tg.create_task(parse_diet_plan(req.result()))
            )

    for i in range(len(parsed_meal_plans)):
        parsed_meal_plans[i] = parsed_meal_plans[i].result()

    return parsed_meal_plans


async def compound_most_optimal_meal_plan(
        diet_plan_variations: list[list[dict]], daily_calories_goal: int, plan_length: int = 7
) -> dict[int, dict[str, Any]]:
    daily_micronutrients = []
    optimal_meal_plan: dict[int, dict] = {}
    meal_plan_variations_structured: list[dict[int, dict]] = []

    async with asyncio.TaskGroup() as tg:
        for plan in diet_plan_variations:
            daily_micronutrients.append(
                tg.create_task(calculate_total_daily_micronutrients(plan))
            )

    for i in range(len(diet_plan_variations)):
        meal_plan: dict[int, dict[str, Any]] = {}
        for meal in diet_plan_variations[i]:
            if (day := meal["day"]) not in meal_plan:
                meal_plan[day] = {
                    "meals": [],
                    "total": daily_micronutrients[i].result()[day],
                }

            meal_plan[day]["meals"].append(meal)

        meal_plan_variations_structured.append(meal_plan)

    daily_calories_goal_diff: dict[int, int] = {
        k: 9999 for k in range(1, plan_length + 1)
    }
    for i in range(len(meal_plan_variations_structured)):
        for day in meal_plan_variations_structured[i]:
            day = int(day)
            diff = abs(
                meal_plan_variations_structured[i][day]["total"]["calories"]
                - daily_calories_goal
            )
            if diff < daily_calories_goal_diff[day]:
                optimal_meal_plan[day] = meal_plan_variations_structured[i][day]
                daily_calories_goal_diff[day] = diff

    return optimal_meal_plan


def _to_snake_case(s):
    s = s.lower()
    s = re.sub(r'\W+', '_', s)
    s = s.strip('_')

    return s


async def generate_images_for_meals(meal_plan: dict):
    snake_cased_meal_names = set()
    meal_names_map = {}
    meal_to_image_map = {}

    for day in meal_plan:
        for meal in meal_plan[day]["meals"]:
            meal_name = _to_snake_case(meal["meal_name"])
            snake_cased_meal_names.add(meal_name)
            meal_names_map[meal_name] = meal["meal_name"]

    unmatched_meals = []
    for meal_name in snake_cased_meal_names:
        key = datastore_client.key("MealImage", meal_name)
        meal_obj = datastore_client.get(key)
        if meal_obj is None:
            unmatched_meals.append(meal_name)

    async with asyncio.TaskGroup() as tg:
        for meal_name in unmatched_meals:
            meal_to_image_map[meal_name] = tg.create_task(
                openai_get_generated_image_url(f"{meal_names_map[meal_name]} on the kitchen table")
            )

    dest_bucket = storage_client.bucket(DESTINATION_BUCKET)

    for meal_name in meal_to_image_map:
        image_url = meal_to_image_map[meal_name].result()

        async with http_client.session.get(image_url) as response:
            raw_img = BytesIO(await response.content.read())
            raw_img.seek(0)
            dest_blob = dest_bucket.blob(f"{meal_name}.png")
            dest_blob.upload_from_file(raw_img, content_type="image/png")

        key = datastore_client.key("MealImage", meal_name)
        meal_obj = datastore.Entity(key=key)
        meal_obj.update({
            "full_name": meal_names_map[meal_name],
            "images": {
                str(i): f"https://static.mealhow.ai/meal-images/{meal_name}_{i}x{i}.jpg" for i in (256, 512, 1024)
            },
        })
        datastore_client.put(meal_obj)


async def main(input_data):
    http_client.start()
    openai.aiosession.set(http_client())

    calories_daily_goal = int(input_data['kcal'])
    diet_plan_request_body = MEAL_PLAN_REQUEST.format(kcal=calories_daily_goal)
    parsed_diet_plans = await request_meal_plans(diet_plan_request_body)
    optimal_meal_plan = await compound_most_optimal_meal_plan(parsed_diet_plans, calories_daily_goal)
    await generate_images_for_meals(optimal_meal_plan)

    await http_client.stop()
    return optimal_meal_plan


@functions_framework.http
def execute(request):
    request_json = request.get_json(silent=True)

    loop = asyncio.new_event_loop()
    task = loop.create_task(main(request_json))
    loop.run_until_complete(task)

    return task.result(), 201
