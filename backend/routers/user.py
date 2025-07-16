# routers/user.py
from fastapi import APIRouter, HTTPException
from schemas.user import UserSignup
from crud.user import create_user

router = APIRouter()

@router.post("/signup")
async def signup(user: UserSignup):
    success = await create_user(user.user_id)
    if not success:
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")
    return {"message": f"{user.user_id}님 가입이 완료되었습니다."}