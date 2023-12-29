import asyncio

import clients
import config
import core
import functions_framework
import mealhow_sdk
import openai


async def main(input_data):
    clients.http_client.start()
    clients.cloud_storage_session.initialise(clients.http_client())
    openai.aiosession.set(clients.http_client())

    calories_daily_goal = int(input_data["kcal"])
    user_id = input_data["user_id"]
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
    await core.save_meal_info_and_generate_images(optimal_meal_plan)
    await core.save_meal_plan(optimal_meal_plan, user_id)
    await clients.http_client.stop()

    return optimal_meal_plan


@functions_framework.http
def execute(request):
    request_json = request.get_json(silent=True)

    loop = asyncio.new_event_loop()
    task = loop.create_task(main(request_json))
    loop.run_until_complete(task)

    return task.result(), 201


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    task = loop.create_task(main({"kcal": 2200, "user_id": "123"}))
    loop.run_until_complete(task)
