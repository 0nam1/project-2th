# backend/schemas/plan.py
from pydantic import BaseModel, Field
from datetime import date
from typing import Literal

class PlanBase(BaseModel):
    plan_date: date
    status: Literal['pending', 'completed', 'skipped'] = 'pending'

class WorkoutPlanCreate(BaseModel):
    exercise_name: str
    reps: int | None = None
    sets: int | None = None
    weight_kg: float | None = None
    duration_min: int | None = None

class WorkoutPlan(PlanBase, WorkoutPlanCreate):
    id: int
    user_id: str

    class Config:
        from_attributes = True

class DietPlanCreate(BaseModel):
    food_name: str
    calories: int | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None

class DietPlan(PlanBase, DietPlanCreate):
    id: int
    user_id: str

    class Config:
        from_attributes = True
