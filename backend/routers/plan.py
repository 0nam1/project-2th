# backend/routers/plan.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from datetime import date
from ..schemas.plan import WorkoutPlan, DietPlan # DietPlan 추가
from ..crud import plan as plan_crud
from ..crud import meal as meal_crud # meal_crud 추가
from ..dependencies import get_current_user

router = APIRouter(prefix="/plans", tags=["plans"])

@router.get("/range/{start_date}/{end_date}", response_model=Dict[str, Any]) # 응답 모델 변경
async def read_plans_for_range(
    start_date: date,
    end_date: date,
    current_user: dict = Depends(get_current_user)
):
    """캘린더에 표시할 특정 날짜 범위의 모든 운동 및 식단 계획을 가져옵니다."""
    user_id = current_user['user_id']
    workout_plans_raw = await plan_crud.get_plans_by_range(user_id, start_date, end_date)
    diet_plans_raw = await meal_crud.get_diet_plans_by_range(user_id, start_date, end_date) # 식단 계획 가져오기

    # Record 객체를 Pydantic 모델로 변환
    workout_plans = [WorkoutPlan.from_orm(plan) for plan in workout_plans_raw]
    diet_plans = [DietPlan.from_orm(plan) for plan in diet_plans_raw]

    return {
        "workout_plans": workout_plans,
        "diet_plans": diet_plans
    }

# 기존 /month 엔드포인트는 더 이상 사용하지 않으므로 삭제하거나 주석 처리할 수 있습니다。
# @router.get("/month/{year}/{month}", response_model=List[WorkoutPlan])
# async def read_plans_for_month(
#     year: int,
#     month: int,
#     current_user: dict = Depends(get_current_user)
# ):
#     """캘린더에 표시할 특정 월의 모든 운동 계획을 가져옵니다."""
#     if not (1 <= month <= 12):
#         raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
    
#     user_id = current_user['user_id']
#     plans = await plan_crud.get_plans_by_month(user_id, year, month)
#     return plans
    return plans