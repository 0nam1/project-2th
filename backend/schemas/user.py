# schemas/user.py
from pydantic import BaseModel

class UserSignup(BaseModel):
    user_id: str
    gender: str
    age: int
    height: float
    weight: float
    level: int
    injury_level: str | None = None
    injury_part: str | None = None

class UserLogin(BaseModel):
    user_id: str