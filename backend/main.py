# main.py
from fastapi import FastAPI
from database import database
from routers import user, protected, chat, tts, batch_tts  # ← user.py는 routers/ 폴더 안에 있어야 함
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI()

# frontend 폴더 경로 잡기 (main.py 기준으로 one-level up + frontend)
FRONTEND_PATH = os.path.join(os.path.dirname(__file__), '..', 'frontend')

# CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 중에는 * (모든 도메인) 허용, 배포 시엔 도메인을 지정하는 게 좋음
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


app.include_router(user.router)
app.include_router(protected.router)
app.include_router(chat.router)
app.include_router(tts.router)
app.include_router(batch_tts.router)

# 정적 파일 마운트
app.mount("/", StaticFiles(directory=FRONTEND_PATH, html=True), name="static")