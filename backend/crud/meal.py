from database import database
from schemas.plan import DietPlanCreate
from datetime import date

async def create_diet_plan(user_id: str, plan_date: date, meal_type: str, plan: DietPlanCreate):
    query = """
        INSERT INTO diet_plans (user_id, plan_date, meal_type, food_name, calories, protein_g, carbs_g, fat_g)
        VALUES (:user_id, :plan_date, :meal_type, :food_name, :calories, :protein_g, :carbs_g, :fat_g)
        ON DUPLICATE KEY UPDATE 
            food_name=VALUES(food_name), calories=VALUES(calories), protein_g=VALUES(protein_g), carbs_g=VALUES(carbs_g), fat_g=VALUES(fat_g), status='pending'
    """
    values = {"user_id": user_id, "plan_date": plan_date, "meal_type": meal_type, **plan.dict()}
    await database.execute(query=query, values=values)

async def update_diet_plan_status(user_id: str, plan_date: date, meal_type: str, status: str):
    query = "UPDATE diet_plans SET status = :status WHERE user_id = :user_id AND plan_date = :plan_date AND meal_type = :meal_type"
    await database.execute(query=query, values={"user_id": user_id, "plan_date": plan_date, "meal_type": meal_type, "status": status})

async def update_all_diet_plans_status_for_date(user_id: str, plan_date: date, status: str):
    query = "UPDATE diet_plans SET status = :status WHERE user_id = :user_id AND plan_date = :plan_date"
    await database.execute(query=query, values={"user_id": user_id, "plan_date": plan_date, "status": status})

async def get_diet_plans_by_range(user_id: str, start_date: date, end_date: date):
    query = """
        SELECT id, user_id, plan_date, meal_type, food_name, calories, protein_g, carbs_g, fat_g, status 
        FROM diet_plans 
        WHERE user_id = :user_id AND plan_date BETWEEN :start_date AND :end_date
        ORDER BY plan_date
    """
    return await database.fetch_all(query=query, values={"user_id": user_id, "start_date": start_date, "end_date": end_date})
