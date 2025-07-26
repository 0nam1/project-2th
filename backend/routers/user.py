# routers/user.py
from fastapi import APIRouter, HTTPException
from schemas.user import UserSignup, UserLogin
from crud.user import verify_user, create_user
from utils.jwt_handler import create_access_token

router = APIRouter(prefix="/users")

@router.post("/signup")
async def signup(user: UserSignup):
    success = await create_user(user)
    if not success:
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")

    # ✅ JWT 토큰 생성
    access_token = create_access_token(data={"sub": user.user_id})

    # ✅ 메시지 + 토큰 반환
    return {
        "message": f"{user.user_id}님 가입이 완료되었습니다.",
        "access_token": access_token
    }

@router.post("/login")
async def login(user: UserLogin):
    is_valid = await verify_user(user.user_id)
    if not is_valid:
        raise HTTPException(status_code=404, detail="존재하지 않는 사용자입니다.")
    # ✅ JWT 토큰 생성
    access_token = create_access_token(data={"sub": user.user_id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }