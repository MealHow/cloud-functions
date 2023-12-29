import asyncio
from typing import Any

import clients
import cloud
import config
import core
import functions_framework
import mealhow_sdk
import openai


async def main(input_data: dict) -> dict:
    prompt = await mealhow_sdk.get_openai_meal_plan_prompt(
        mealhow_sdk.MealPlanPromptInputData(
            calories_goal=input_data["calories_goal"],
            protein_goal=input_data.get("protein_goal", None),
            preparation_time=input_data.get("preparation_time", None),
            preferred_cuisines=input_data.get("preferred_cuisines", []),
            ingredients_to_avoid=input_data.get("ingredients_to_avoid", []),
            health_issues=input_data.get("health_issues", []),
        )
    )
    clients.http_client.start()
    clients.cloud_storage_session.initialise(clients.http_client())
    openai.aiosession.set(clients.http_client())

    user_id = input_data["user_id"]
    parsed_diet_plans = await mealhow_sdk.request_meal_plans(
        request_body=prompt,
        gpt_model=config.OPENAI_GPT_MODEL_VERSION,
    )
    optimal_meal_plan = await mealhow_sdk.compound_most_optimal_meal_plan(
        diet_plan_variations=parsed_diet_plans,
        daily_calories_goal=input_data["calories_goal"],
    )

    await asyncio.gather(
        core.save_meal_info_and_generate_images(optimal_meal_plan),
        cloud.save_meal_plan(optimal_meal_plan, user_id),
    )
    await clients.http_client.stop()

    return optimal_meal_plan


@functions_framework.http
def execute(request: Any) -> tuple:
    request_json = request.get_json(silent=True)

    loop = asyncio.new_event_loop()
    task = loop.create_task(main(request_json))
    loop.run_until_complete(task)

    return task.result(), 201


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    task = loop.create_task(main({"calories_goal": 2200, "user_id": "test"}))
    loop.run_until_complete(task)
