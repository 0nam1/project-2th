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