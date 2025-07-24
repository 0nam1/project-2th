# backend/crud/plan.py
from ..database import database
from ..schemas.plan import WorkoutPlanCreate
from datetime import date

async def create_workout_plan(user_id: str, plan_date: date, plan: WorkoutPlanCreate):
    query = """
        INSERT INTO workout_plans (user_id, plan_date, exercise_name, reps, sets, weight_kg, duration_min)
        VALUES (:user_id, :plan_date, :exercise_name, :reps, :sets, :weight_kg, :duration_min)
        ON DUPLICATE KEY UPDATE 
            reps=VALUES(reps), sets=VALUES(sets), weight_kg=VALUES(weight_kg), duration_min=VALUES(duration_min), status='pending'
    """
    values = {"user_id": user_id, "plan_date": plan_date, **plan.dict()}
    await database.execute(query=query, values=values)

async def update_workout_plan_status(user_id: str, plan_date: date, status: str):
    query = "UPDATE workout_plans SET status = :status WHERE user_id = :user_id AND plan_date = :plan_date"
    await database.execute(query=query, values={"user_id": user_id, "plan_date": plan_date, "status": status})

async def get_plans_by_month(user_id: str, year: int, month: int):
    query = """
        SELECT id, user_id, plan_date, exercise_name, reps, sets, weight_kg, duration_min, status 
        FROM workout_plans 
        WHERE user_id = :user_id AND YEAR(plan_date) = :year AND MONTH(plan_date) = :month
        ORDER BY plan_date
    """
    return await database.fetch_all(query=query, values={"user_id": user_id, "year": year, "month": month})

async def get_plans_by_range(user_id: str, start_date: date, end_date: date):
    query = """
        SELECT id, user_id, plan_date, exercise_name, reps, sets, weight_kg, duration_min, status 
        FROM workout_plans 
        WHERE user_id = :user_id AND plan_date BETWEEN :start_date AND :end_date
        ORDER BY plan_date
    """
    return await database.fetch_all(query=query, values={"user_id": user_id, "start_date": start_date, "end_date": end_date})

# (필요시 DietPlan 관련 CRUD 함수들도 여기에 추가)