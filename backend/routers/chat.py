import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, List, AsyncGenerator
from datetime import date, timedelta

from ..dependencies import get_current_user
from ..utils.openai_client import chat_client, CHAT_DEPLOYMENT_NAME, ask_openai_unified, get_embedding, should_search_long_term_memory
from ..utils.ollama_client import ask_ollama_stream
from ..crud.chat import save_chat_history, retrieve_and_rerank_history
from ..crud import plan as plan_crud
from ..schemas.chat import ChatHistoryCreate
from ..schemas.plan import WorkoutPlanCreate
from ..utils.youtube_search import search_youtube_videos

router = APIRouter()

# --- In-memory Cache ---
chat_cache: Dict[str, List[Dict]] = {}
CACHE_MAX_LENGTH = 10

# -------------------------------------
# 1. AI 분석 및 계획 관리 로직
# -------------------------------------

async def analyze_user_intent(user_id: str, message: str, history: List[Dict]):
    """사용자의 의도를 분석하여 '수행 완료'인지, '계획 변경'인지, 아니면 '일반 대화/루틴 요청'인지 분류합니다."""
    system_prompt = f"""
    당신은 사용자의 의도를 분석하는 AI입니다. 사용자의 최근 메시지와 대화 기록을 바탕으로 다음 중 하나의 카테고리로 분류해주세요.
    1. 'complete_today': 사용자가 오늘 계획된 운동을 완료했다고 보고하는 경우. (예: "오늘 운동 다 했어", "추천해준거 끝냈어")
    2. 'modify_today': 사용자가 오늘 계획과 다른 운동을 수행했다고 보고하는 경우. (예: "오늘 벤치프레스 50kg 5x5만 했어")
    3. 'general_chat': 일반적인 대화 또는 새로운 운동 루틴을 요청하는 경우. (예: "안녕?", "일주일치 루틴 짜줘")

    오늘 날짜: {date.today().isoformat()}
    사용자 ID: {user_id}

    분석 후, 다음 JSON 형식 중 하나로만 답변해주세요.
    - 완료 보고 시: {{"intent": "complete_today"}}
    - 변경 보고 시: {{"intent": "modify_today", "new_plan": "사용자가 실제 수행한 운동 내용"}}
    - 일반 대화 시: {{"intent": "general_chat"}}
    """
    try:
        response = await chat_client.chat.completions.create(
            model=CHAT_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                *history,
                {"role": "user", "content": message}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {"intent": "general_chat"} # 오류 발생 시 일반 대화로 처리

async def parse_and_save_routine(user_id: str, ai_response: str):
    """AI의 답변에서 운동 루틴을 파싱하여 DB에 저장합니다."""
    system_prompt = f"""
    당신은 AI 트레이너의 답변에서 날짜별 운동 계획을 추출하여 JSON으로 변환하는 시스템입니다.
    'n일차', 'n주차', '월요일' 같은 날짜 정보를 오늘({date.today().isoformat()})부터 시작하는 절대 날짜(YYYY-MM-DD)로 변환해야 합니다.
    각 운동 항목은 exercise_name, reps, sets, weight_kg, duration_min 필드를 가져야 합니다. 정보가 없으면 null로 처리하세요.

    출력 형식: {{"plans": [{{ "date": "YYYY-MM-DD", "exercises": [...] }}]}}
    만약 AI 답변이 운동 루틴이 아니거나 파싱할 수 없으면, {{"plans": []}} 를 반환하세요.
    
    예시 입력:
    "1일차: 스쿼트 12회 5세트, 런지 15회 3세트\n2일차: 벤치프레스 10회 5세트 60kg"
    예시 출력:
    {{
        "plans": [
            {{"date": "{date.today().isoformat()}", "exercises": [
                {{"exercise_name": "스쿼트", "reps": 12, "sets": 5, "weight_kg": None, "duration_min": None}},
                {{"exercise_name": "런지", "reps": 15, "sets": 3, "weight_kg": None, "duration_min": None}}
            ]}},
            {{"date": "{(date.today() + timedelta(days=1)).isoformat()}", "exercises": [
                {{"exercise_name": "벤치프레스", "reps": 10, "sets": 5, "weight_kg": 60, "duration_min": None}}
            ]}}
        ]
    }}
    """
    try:
        response = await chat_client.chat.completions.create(
            model=CHAT_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": ai_response}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        parsed_data = json.loads(response.choices[0].message.content)

        for day_plan in parsed_data.get("plans", []):
            plan_date = date.fromisoformat(day_plan["date"])
            for exercise in day_plan["exercises"]:
                workout_plan = WorkoutPlanCreate(**exercise)
                await plan_crud.create_workout_plan(user_id, plan_date, workout_plan)
        
        print(f"[INFO] Workout plan saved for user {user_id}")

    except Exception as e:
        print(f"[ERROR] Failed to parse or save routine: {e}")


# -------------------------------------
# 2. 채팅 스트림 및 메인 로직
# -------------------------------------

async def stream_generator(
    user_id: str, user_message: str, image_bytes: bytes | None, model: str
) -> AsyncGenerator[str, None]:
    """AI의 답변을 스트리밍하고, 끝나면 대화 기록 저장 및 루틴 파싱을 수행합니다."""
    full_response = ""
    recent_history = chat_cache.get(user_id, [])
    rag_history = []
    embedding = None

    # RAG (장기기억) 검색 - OpenAI 모델 사용 시에만
    if model == "gpt-4o":
        if await should_search_long_term_memory(user_message, recent_history):
            embedding = await get_embedding(user_message)
            rag_history = await retrieve_and_rerank_history(user_id, user_message, embedding)
        if embedding is None and user_message:
            embedding = await get_embedding(user_message)

    # AI 답변 스트리밍
    if model == "llama3.2:1b":
        response_stream = ask_ollama_stream(user_message, recent_history)
        async for chunk in response_stream:
            full_response += chunk
            yield chunk
    else:
        response_stream = await ask_openai_unified(user_message, image_bytes, recent_history, rag_history)
        async for chunk in response_stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield content
    
    # 스트리밍 종료 후 작업
    # 1. 대화 기록 저장
    user_chat = ChatHistoryCreate(user_id=user_id, role_type="user", content=user_message, embedding=embedding)
    assistant_chat = ChatHistoryCreate(user_id=user_id, role_type="assistant", content=full_response)
    await save_chat_history(user_chat)
    await save_chat_history(assistant_chat)

    # 2. 인메모리 캐시 업데이트
    chat_cache.setdefault(user_id, []).extend([
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": full_response}
    ])
    chat_cache[user_id] = chat_cache[user_id][-CACHE_MAX_LENGTH:]

    # 3. AI 답변이 루틴인지 분석하고 DB에 저장 (백그라운드 실행)
    asyncio.create_task(parse_and_save_routine(user_id, full_response))


@router.post("/chat/image")
async def chat_with_text_or_image(
    message: str = Form(""),
    image: UploadFile = File(None),
    model: str = Form("gpt-4o"),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user['user_id']
    recent_history = chat_cache.get(user_id, [])
    
    # 1. 사용자의 의도 분석
    intent_data = await analyze_user_intent(user_id, message, recent_history)
    intent = intent_data.get("intent")

    # 2. 의도에 따른 분기 처리
    if intent == "complete_today":
        await plan_crud.update_workout_plan_status(user_id, date.today(), 'completed')
        return JSONResponse(content={"message": "오늘의 운동 완료 처리되었습니다! 수고하셨습니다."})

    elif intent == "modify_today":
        # TODO: 이 경우, 사용자가 말한 운동으로 오늘 plan을 덮어쓰는 로직 추가 필요
        # 우선은 완료 처리만 함
        await plan_crud.update_workout_plan_status(user_id, date.today(), 'completed')
        return JSONResponse(content={"message": "운동 기록이 저장되었습니다. 멋져요!"})
    
    # 3. 일반 대화 또는 루틴 요청 시, 스트리밍 응답 생성
    else: # general_chat
        try:
            image_bytes = await image.read() if image else None
            return StreamingResponse(
                stream_generator(user_id, message, image_bytes, model),
                media_type="text/event-stream"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------
# 3. YouTube 검색 (기존과 동일)
# -------------------------------------
@router.get("/youtube_search")
async def get_youtube_videos(
    ai_response: str = Query(..., alias="query"),
    max_results: int = Query(3, ge=1, le=10),
    current_user: dict = Depends(get_current_user)
):
    # (이하 로직은 기존과 동일하게 유지)
    try:
        youtube_query_prompt = f"다음 텍스트에서 YouTube에서 검색할 운동 루틴 관련 키워드를 3개 이내로 추출해줘. 텍스트가 운동 루틴과 관련이 없다면 'None'이라고만 답변해줘. 텍스트: '{ai_response}'"
        
        youtube_keyword_response = await chat_client.chat.completions.create(
            model=CHAT_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "You are a keyword extraction assistant."},
                {"role": "user", "content": youtube_query_prompt}
            ],
            temperature=0.0,
            max_tokens=50
        )
        
        youtube_keywords = youtube_keyword_response.choices[0].message.content.strip()

        if youtube_keywords.lower() != 'none':
            search_term = youtube_keywords.split(',')[0].strip()
            youtube_results = await search_youtube_videos(search_term, max_results)
            if youtube_results["success"]:
                return JSONResponse(content=youtube_results["videos"])
            else:
                raise HTTPException(status_code=404, detail=youtube_results["message"])
        else:
            return JSONResponse(content=[], status_code=200)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))