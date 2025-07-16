# schemas/user.py
from pydantic import BaseModel

class UserSignup(BaseModel):
    user_id: str