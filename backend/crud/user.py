# crud/user.py
from database import database
from schemas.user import UserSignup

async def create_user(user: UserSignup):
    # 1. 먼저 동일한 user_id가 이미 존재하는지 확인
    check_query = "SELECT 1 FROM users WHERE user_id = :user_id"
    existing = await database.fetch_one(query=check_query, values={"user_id": user.user_id})
    
    if existing:
        return False  # 이미 존재함

    # 2. 존재하지 않는다면 새로 INSERT
    insert_query = """
        INSERT INTO users (user_id, gender, age, height, weight, level, injury_level, injury_part)
        VALUES (:user_id, :gender, :age, :height, :weight, :level, :injury_level, :injury_part)
    """
    await database.execute(query=insert_query, values={
        "user_id": user.user_id,
        "gender": user.gender,
        "age": user.age,
        "height": user.height,
        "weight": user.weight,
        "level": user.level,
        "injury_level": user.injury_level,
        "injury_part": user.injury_part,
    })
    return True
    
async def verify_user(user_id: str) -> bool:
    query = "SELECT user_id FROM users WHERE user_id = :user_id"
    result = await database.fetch_one(query=query, values={"user_id": user_id})
    return result is not None