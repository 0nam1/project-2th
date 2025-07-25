# routers/protected.py

from fastapi import APIRouter, Depends, HTTPException
from ..dependencies import get_current_user
from ..crud.user import get_user_by_id

router = APIRouter(prefix="/protected", tags=["보호된 API"])

@router.get("/main")
async def read_main(current_user: dict = Depends(get_current_user)):
    return {"message": f"{current_user['user_id']}님, 메인 페이지에 오신 걸 환영합니다!"}

@router.get("/me")
async def read_user_info(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자 정보를 찾을 수 없습니다.")
    return {"user": user}