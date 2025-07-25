from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import date
from ..schemas.plan import DietPlan, DietPlanCreate
from ..crud import meal as meal_crud
from ..dependencies import get_current_user

router = APIRouter(prefix="/diet_plans", tags=["diet_plans"])

@router.post("/{plan_date}/{meal_type}", response_model=DietPlan)
async def create_diet_plan(
    plan_date: date,
    meal_type: str,
    plan: DietPlanCreate,
    current_user: dict = Depends(get_current_user)
):
    """새로운 식단 계획을 생성하거나 기존 식단 계획을 업데이트합니다."""
    user_id = current_user['user_id']
    await meal_crud.create_diet_plan(user_id, plan_date, meal_type, plan)
    # TODO: 실제 생성된 DietPlan 객체를 반환하도록 수정 필요
    # 현재는 임시로 DietPlanCreate 객체를 DietPlan으로 변환하여 반환
    return DietPlan(user_id=user_id, plan_date=plan_date, meal_type=meal_type, **plan.dict())

@router.get("/range/{start_date}/{end_date}", response_model=List[DietPlan])
async def read_diet_plans_for_range(
    start_date: date,
    end_date: date,
    current_user: dict = Depends(get_current_user)
):
    """캘린더에 표시할 특정 날짜 범위의 모든 식단 계획을 가져옵니다."""
    user_id = current_user['user_id']
    plans = await meal_crud.get_diet_plans_by_range(user_id, start_date, end_date)
    return plans

@router.put("/{plan_date}/{meal_type}/status/{status}", response_model=DietPlan)
async def update_diet_plan_status(
    plan_date: date,
    meal_type: str,
    status: str,
    current_user: dict = Depends(get_current_user)
):
    """식단 계획의 상태를 업데이트합니다."""
    user_id = current_user['user_id']
    await meal_crud.update_diet_plan_status(user_id, plan_date, meal_type, status)
    # TODO: 실제 업데이트된 DietPlan 객체를 반환하도록 수정 필요
    # 현재는 임시로 DietPlan 객체를 반환
    return DietPlan(user_id=user_id, plan_date=plan_date, meal_type=meal_type, food_name="", status=status)
