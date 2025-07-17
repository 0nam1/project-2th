# routers/protected.py

from fastapi import APIRouter, Depends
from dependencies import get_current_user

router = APIRouter(prefix="/protected", tags=["보호된 API"])

@router.get("/main")
async def read_main(current_user: dict = Depends(get_current_user)):
    return {"message": f"{current_user['user_id']}님, 메인 페이지에 오신 걸 환영합니다!"}