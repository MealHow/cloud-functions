import asyncio
import base64
import datetime
import json

import clients
import cloud
import config
import core
import functions_framework
import mealhow_sdk
import openai
from cloudevents.http.event import CloudEvent
from google.cloud import ndb
from mealhow_sdk import enums
from mealhow_sdk.datastore_models import MealPlan, User


async def main(input_data: dict) -> None:
    clients.http_client.start()
    clients.cloud_storage_session.initialise(clients.http_client())
    openai.aiosession.set(clients.http_client())

    with clients.ndb_client.context():
        user_key = ndb.Key(User, input_data["user_id"])

        new_meal_plan = (
            MealPlan.query()
            .filter(ndb.AND(MealPlan.user == user_key, MealPlan.status == enums.MealPlanStatus.failed.name))
            .get()
        )
        if new_meal_plan:
            new_meal_plan.status = enums.MealPlanStatus.in_progress.name
            new_meal_plan.put()
        else:
            new_meal_plan = MealPlan(user=user_key, status=enums.MealPlanStatus.in_progress.name)
            current_active_meal_plan = (
                MealPlan.query()
                .filter(ndb.AND(MealPlan.user == user_key, MealPlan.status == enums.MealPlanStatus.active.name))
                .get()
            )
            if current_active_meal_plan:
                current_active_meal_plan.status = enums.MealPlanStatus.archived.name
                ndb.put_multi([current_active_meal_plan, new_meal_plan])
            else:
                new_meal_plan.put()

        user = User.get_by_id(user_key.id())

    try:
        prompt = await mealhow_sdk.get_openai_meal_plan_prompt(
            mealhow_sdk.MealPlanPromptInputData(
                calories_goal=user.calories_goal,
                protein_goal=user.protein_goal,
                preparation_time=user.meal_prep_time,
                preferred_cuisines=user.preferred_cuisines,
                ingredients_to_avoid=user.avoid_foods,
                health_issues=user.health_conditions,
            )
        )

        parsed_diet_plans = await mealhow_sdk.request_meal_plans(
            request_body=prompt,
            gpt_model=config.OPENAI_GPT_MODEL_VERSION,
        )
        optimal_meal_plan = await mealhow_sdk.compound_most_optimal_meal_plan(
            diet_plan_variations=parsed_diet_plans,
            daily_calories_goal=user.calories_goal,
        )

        await asyncio.gather(
            core.save_meal_info_and_generate_images(optimal_meal_plan),
            cloud.save_meal_plan(optimal_meal_plan, new_meal_plan.key.id()),
        )

    except Exception as e:
        with clients.ndb_client.context():
            new_meal_plan.status = enums.MealPlanStatus.failed.name
            new_meal_plan.put()

        raise e
    else:
        with clients.ndb_client.context():
            meal_plan_obj = MealPlan.get_by_id(new_meal_plan.key.id())
            meal_plan_obj.status = enums.MealPlanStatus.active.name
            user.last_requested_meal_plan_at = datetime.datetime.now()
            ndb.put_multi([meal_plan_obj, user])

    await clients.http_client.stop()


@functions_framework.cloud_event
def execute(cloud_event: CloudEvent) -> None:
    input_data = json.loads(base64.b64decode(cloud_event.data["message"]["data"]))

    loop = asyncio.new_event_loop()
    task = loop.create_task(main(input_data))
    loop.run_until_complete(task)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    task = loop.create_task(main({"user_id": "auth0|6590561b6876005900685b8b"}))
    loop.run_until_complete(task)
