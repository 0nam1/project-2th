# main.py
from fastapi import FastAPI
from database import database
from routers import user  # ← user.py는 routers/ 폴더 안에 있어야 함

app = FastAPI()

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

app.include_router(user.router, prefix="/users")