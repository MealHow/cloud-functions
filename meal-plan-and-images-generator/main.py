import asyncio

import functions_framework
import mealhow_sdk
import openai

import clients
import config
import core


async def main(input_data):
    clients.http_client.start()
    openai.aiosession.set(clients.http_client())

    calories_daily_goal = int(input_data['kcal'])
    diet_plan_request_body = config.MEAL_PLAN_PROMPT.format(kcal=calories_daily_goal)
    parsed_diet_plans = await mealhow_sdk.request_meal_plans(
        request_body=diet_plan_request_body,
        gpt_model=config.OPENAI_GPT_MODEL_VERSION,
    )
    optimal_meal_plan = await mealhow_sdk.compound_most_optimal_meal_plan(
        diet_plan_variations=parsed_diet_plans,
        daily_calories_goal=calories_daily_goal,
    )

    await core.generate_images_for_meals(optimal_meal_plan)
    await clients.http_client.stop()

    return optimal_meal_plan


@functions_framework.http
def execute(request):
    request_json = request.get_json(silent=True)

    loop = asyncio.new_event_loop()
    task = loop.create_task(main(request_json))
    loop.run_until_complete(task)

    return task.result(), 201
