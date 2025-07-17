# crud/user.py
from database import database
from sqlalchemy.exc import IntegrityError


async def create_user(user_id: str):
    query = "INSERT INTO users (user_id) VALUES (:user_id)"
    try:
        await database.execute(query=query, values={"user_id": user_id})
        return True
    except IntegrityError:
        return False
    
async def verify_user(user_id: str) -> bool:
    query = "SELECT user_id FROM users WHERE user_id = :user_id"
    result = await database.fetch_one(query=query, values={"user_id": user_id})
    return result is not None