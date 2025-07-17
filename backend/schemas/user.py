# schemas/user.py
from pydantic import BaseModel

class UserSignup(BaseModel):
    user_id: str

class UserLogin(BaseModel):
    user_id: str