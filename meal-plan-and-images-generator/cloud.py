import io

import clients
import config
from google.cloud import ndb
from google.cloud.ndb import Future
from mealhow_sdk.datastore_models import (
    Meal,
    MealImage,
    MealImageThumbnail,
    MealPlan,
    MealPlanDayItem,
    MealPlanDayTotalInfo,
    MealPlanDetails,
    MealPlanItem,
    User,
)


async def upload_raw_image_on_cloud_storage(blob: bytes, meal_name: str) -> None:
    raw_img = io.BytesIO(blob)
    raw_img.seek(0)
    await clients.cloud_storage_session().upload(
        bucket=config.DESTINATION_BUCKET, object_name=f"{meal_name}.png", file_data=raw_img, content_type="image/png"
    )


async def get_meal_image_entities_by_ids(meal_name_ids: set[str]) -> set:
    with clients.ndb_client.context():
        keys = [ndb.Key(MealImage, meal_id) for meal_id in meal_name_ids]
        return {i.key.id() for i in ndb.get_multi(keys) if i is not None}


async def save_new_meal_info_and_image(meal_image_id: str, meal_obj: dict) -> Future:
    with clients.ndb_client.context():
        meal_image_key = ndb.Key(MealImage, meal_image_id)
        meal_image = MealImage(
            key=meal_image_key,
            images=[
                MealImageThumbnail(
                    size=size,
                    url=f"{config.CDN_URL_PREFIX}{meal_image_id}_{size}x{size}.jpg",
                )
                for size in config.IMAGE_SIZES
            ],
        )
        meal_image.put()

        meal_key = ndb.Key(Meal, meal_obj["id"])
        meal = Meal(
            key=meal_key,
            full_name=meal_obj["meal_name"],
            calories=int(meal_obj["calories"]),
            carbs=int(meal_obj["carbs"]),
            fats=int(meal_obj["fats"]),
            protein=int(meal_obj["protein"]),
            preparation_time=int(meal_obj["preparation_time"]),
            image=meal_image_key,
        )

        return meal.put_async()


async def save_meal_plan(meal_plan: dict, user_id: str) -> None:
    with clients.ndb_client.context():
        user_key = ndb.Key(User, user_id)

        current_active_meal_plan = (
            MealPlan.query().filter(ndb.AND(MealPlan.user == user_key, MealPlan.active == True)).get()  # noqa: E712
        )

        meal_plan_details = {}
        for day in meal_plan:
            day_meals = meal_plan[day]["meals"]

            meal_plan_details[f"day_{day}"] = MealPlanDayItem(
                meals=[
                    MealPlanItem(
                        id=day_meals[i]["id"],
                        meal_name=day_meals[i]["meal_name"],
                        meal_time=day_meals[i]["meal_time"],
                        day=int(day_meals[i]["day"]),
                        preparation_time=int(day_meals[i]["preparation_time"]),
                        calories=int(day_meals[i]["calories"]),
                        protein=int(day_meals[i]["protein"]),
                        carbs=int(day_meals[i]["carbs"]),
                        fats=int(day_meals[i]["fats"]),
                    )
                    for i in range(len(day_meals))
                ],
                total=MealPlanDayTotalInfo(
                    calories=int(meal_plan[day]["total"]["calories"]),
                    carbs=int(meal_plan[day]["total"]["carbs"]),
                    fats=int(meal_plan[day]["total"]["fats"]),
                    protein=int(meal_plan[day]["total"]["protein"]),
                ),
            )

        meal_plan_obj = MealPlan(user=user_key, details=MealPlanDetails(**meal_plan_details))
        meal_plan_obj.put()

        if current_active_meal_plan is not None:
            current_active_meal_plan.active = False
            current_active_meal_plan.put()
