import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, List, AsyncGenerator
from datetime import date, timedelta

from dependencies import get_current_user
from utils.openai_client import chat_client, CHAT_DEPLOYMENT_NAME, ask_openai_unified, get_embedding, should_search_long_term_memory
from utils.ollama_client import ask_ollama_stream
from crud.chat import save_chat_history, retrieve_and_rerank_history
from crud import plan as plan_crud
from crud import meal as meal_crud
from crud.user import get_user_by_id # 사용자 정보 조회를 위해 import
from schemas.chat import ChatHistoryCreate
from schemas.plan import WorkoutPlanCreate, DietPlanCreate
from utils.youtube_search import search_youtube_videos

router = APIRouter()

# --- In-memory Cache ---
chat_cache: Dict[str, List[Dict]] = {}
CACHE_MAX_LENGTH = 10

# -------------------------------------
# 1. AI 분석 및 계획 관리 로직 (기존과 동일)
# -------------------------------------

async def analyze_user_intent(user_id: str, message: str, history: List[Dict]):
    """사용자의 의도를 분석하여 '수행 완료'인지, '계획 변경'인지, 아니면 '일반 대화/루틴 요청'인지 분류합니다."""
    system_prompt = f"""
    당신은 사용자의 의도를 분석하는 AI입니다. 사용자의 최근 메시지와 대화 기록을 바탕으로 다음 중 하나의 카테고리로 분류해주세요.
    1. 'complete_workout': 사용자가 오늘 계획된 운동을 완료했다고 보고하는 경우. (예: "오늘 운동 다 했어", "추천해준거 끝냈어")
    2. 'modify_workout': 사용자가 오늘 계획과 다른 운동을 수행했다고 보고하는 경우. (예: "오늘 벤치프레스 50kg 5x5만 했어")
    3. 'complete_meal': 사용자가 오늘 계획된 식사를 완료했다고 보고하는 경우. (예: "오늘 아침 다 먹었어", "점심 먹었어")
    4. 'modify_meal': 사용자가 오늘 계획과 다른 식사를 했다고 보고하는 경우. (예: "오늘 점심은 닭가슴살 샐러드 대신 샌드위치 먹었어")
    5. 'general_chat': 일반적인 대화 또는 새로운 운동 루틴/식단 계획을 요청하는 경우. (예: "안녕?", "일주일치 루틴 짜줘", "식단 짜줘")

    오늘 날짜: {date.today().isoformat()}
    사용자 ID: {user_id}

    분석 후, 다음 JSON 형식 중 하나로만 답변해주세요.
    식사 완료/변경 보고 시, 사용자가 특정 식사 유형(아침, 점심, 저녁, 간식)을 명시하지 않았다면 `meal_type`을 `null`로 반환해주세요.
    - 운동 완료 보고 시: {{"intent": "complete_workout"}}
    - 운동 변경 보고 시: {{"intent": "modify_workout", "new_plan": "사용자가 실제 수행한 운동 내용"}}
    - 식사 완료 보고 시: {{"intent": "complete_meal", "meal_type": "아침/점심/저녁/간식" 또는 null}}
    - 식사 변경 보고 시: {{"intent": "modify_meal", "meal_type": "아침/점심/저녁/간식" 또는 null, "new_plan": "사용자가 실제 수행한 식사 내용"}}
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

async def parse_and_save_plan(user_id: str, ai_response: str):
    """AI의 답변에서 운동 루틴 또는 식단 계획을 파싱하여 DB에 저장합니다."""
    system_prompt = f"""
    당신은 AI 트레이너의 답변에서 날짜별 운동 계획 또는 식단 계획을 추출하여 JSON으로 변환하는 시스템입니다.
    'n일차', 'n주차', '월요일' 같은 날짜 정보를 오늘({date.today().isoformat()})부터 시작하는 절대 날짜(YYYY-MM-DD)로 변환해야 합니다.

    운동 계획의 각 운동 항목은 exercise_name, reps, sets, weight_kg, duration_min 필드를 가져야 합니다. 
    **duration_min은 반드시 분 단위의 정수(integer)여야 합니다.** 정보가 없으면 null로 처리하세요.
    식단 계획의 각 식사 항목은 meal_type (아침, 점심, 저녁, 간식), food_name, calories, protein_g, carbs_g, fat_g 필드를 가져야 합니다. 영양 정보는 가능한 한 구체적인 수치로 제공하고, 정확한 수치를 알 수 없는 경우 일반적인 추정치를 제공하거나 '약 N'과 같이 명시해주세요. **절대 null로 처리하지 말고, 반드시 숫자로 된 값을 제공해야 합니다.**

    출력 형식: {{"plans": [{{ "date": "YYYY-MM-DD", "type": "workout"/"diet", "items": [...] }}]}}
    만약 AI 답변이 운동 루틴이나 식단 계획이 아니거나 파싱할 수 없으면, {{"plans": []}} 를 반환하세요.
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
        print(f"[DEBUG] Parsed data from AI: {parsed_data}") # 디버깅을 위한 출력

        for day_plan in parsed_data.get("plans", []):
            plan_date = date.fromisoformat(day_plan["date"])
            plan_type = day_plan.get("type")

            if plan_type == "workout":
                for exercise in day_plan["items"]:
                    try:
                        if exercise.get("duration_min") is not None:
                            exercise["duration_min"] = int(round(exercise["duration_min"]))
                        
                        workout_plan = WorkoutPlanCreate(**exercise)
                        await plan_crud.create_workout_plan(user_id, plan_date, workout_plan)
                    except Exception as item_e:
                        print(f"[ERROR] Failed to save workout item: {exercise}. Reason: {item_e}")
                print(f"[INFO] Workout plan saved for user {user_id} on {plan_date}")
            elif plan_type == "diet":
                for meal in day_plan["items"]:
                    try:
                        meal_type = meal.pop("meal_type")
                        diet_plan = DietPlanCreate(**meal)
                        await meal_crud.create_diet_plan(user_id, plan_date, meal_type, diet_plan)
                    except Exception as item_e:
                        print(f"[ERROR] Failed to save diet item: {meal}. Reason: {item_e}")
                print(f"[INFO] Diet plan saved for user {user_id} on {plan_date}")
            else:
                print(f"[WARNING] Unknown plan type: {plan_type}")

    except Exception as e:
        print(f"[ERROR] Failed to parse or save routine: {e}")


# -------------------------------------
# 2. 채팅 스트림 및 메인 로직
# -------------------------------------

def create_system_prompt(user_profile: dict) -> str:
    """사용자 프로필을 기반으로 AI에게 전달할 시스템 프롬프트를 생성합니다."""
    injury_info = "없음"
    if user_profile.get('injury_part') and user_profile.get('injury_level'):
        injury_info = f"{user_profile['injury_part']} (수준: {user_profile['injury_level']})"

    return f"""
    당신은 사용자의 개인 정보를 완벽하게 이해하고 맞춤형 답변을 제공하는 AI 퍼스널 트레이너 'GymPT'입니다.

    [사용자 정보]
    - 나이: {user_profile.get('age', '정보 없음')}세
    - 성별: {user_profile.get('gender', '정보 없음')}
    - 키: {user_profile.get('height', '정보 없음')}cm
    - 몸무게: {user_profile.get('weight', '정보 없음')}kg
    - 운동 수준: {user_profile.get('level_desc', f"레벨 {user_profile.get('level', '정보 없음')}")}
    - 부상 정보: {injury_info}

    [당신의 역할]
    1.  **개인화된 조언:** 위 사용자 정보를 반드시 모든 답변의 최우선 고려사항으로 삼으세요.
    2.  **전문적인 트레이너:** 운동 방법, 식단 등에 대해 정확하고 친절하게 설명합니다.
    3.  **동기 부여:** 사용자를 격려하고 긍정적인 태도를 유지합니다.
    """

async def stream_generator(
    user_profile: dict, user_message: str, image_bytes: bytes | None, model: str, ai_prompt_override: str | None = None
) -> AsyncGenerator[str, None]:
    """AI의 답변을 스트리밍하고, 끝나면 대화 기록 저장 및 루틴 파싱을 수행합니다."""
    user_id = user_profile['user_id']
    full_response = ""
    recent_history = chat_cache.get(user_id, [])
    rag_history = []
    embedding = None

    system_prompt = create_system_prompt(user_profile)

    if model == "gpt-4o":
        if await should_search_long_term_memory(user_message, recent_history):
            embedding = await get_embedding(user_message)
            rag_history = await retrieve_and_rerank_history(user_id, user_message, embedding)
        if embedding is None and user_message:
            embedding = await get_embedding(user_message)

    final_user_message = ai_prompt_override if ai_prompt_override else user_message

    if model == "llama3.2:1b":
        response_stream = ask_ollama_stream(final_user_message, recent_history)
        async for chunk in response_stream:
            full_response += chunk
            yield chunk
    else:
        response_stream = await ask_openai_unified(final_user_message, image_bytes, recent_history, rag_history, system_prompt)
        async for chunk in response_stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield content
    
    user_chat = ChatHistoryCreate(user_id=user_id, role_type="user", content=user_message, embedding=embedding)
    assistant_chat = ChatHistoryCreate(user_id=user_id, role_type="assistant", content=full_response)
    await save_chat_history(user_chat)
    await save_chat_history(assistant_chat)

    chat_cache.setdefault(user_id, []).extend([
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": full_response}
    ])
    chat_cache[user_id] = chat_cache[user_id][-CACHE_MAX_LENGTH:]

    asyncio.create_task(parse_and_save_plan(user_id, full_response))


@router.post("/chat/image")
async def chat_with_text_or_image(
    message: str = Form(""),
    image: UploadFile = File(None),
    model: str = Form("gpt-4o"),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user['user_id']
    user_profile = await get_user_by_id(user_id)
    if not user_profile:
        raise HTTPException(status_code=404, detail="사용자 정보를 찾을 수 없습니다.")

    recent_history = chat_cache.get(user_id, [])
    
    intent_data = await analyze_user_intent(user_id, message, recent_history)
    intent = intent_data.get("intent")

    ai_prompt_override = None
    image_bytes = await image.read() if image else None

    if intent == "complete_workout":
        await plan_crud.update_workout_plan_status(user_id, date.today(), 'completed')
        ai_prompt_override = "오늘의 운동을 성공적으로 완료했음을 사용자에게 칭찬하고 격려하는 메시지를 생성해줘."
    elif intent == "modify_workout":
        await plan_crud.update_workout_plan_status(user_id, date.today(), 'completed')
        ai_prompt_override = "운동 기록이 성공적으로 저장되었음을 사용자에게 알리고 격려하는 메시지를 생성해줘."
    elif intent == "complete_meal":
        meal_type = intent_data.get("meal_type")
        if meal_type:
            await meal_crud.update_diet_plan_status(user_id, date.today(), meal_type, 'completed')
            ai_prompt_override = f"오늘의 {meal_type} 식사를 성공적으로 완료했음을 사용자에게 칭찬하고 격려하는 메시지를 생성해줘."
        else:
            await meal_crud.update_all_diet_plans_status_for_date(user_id, date.today(), 'completed')
            ai_prompt_override = "오늘의 모든 식사를 성공적으로 완료했음을 사용자에게 칭찬하고 격려하는 메시지를 생성해줘."
    elif intent == "modify_meal":
        meal_type = intent_data.get("meal_type")
        if meal_type:
            await meal_crud.update_diet_plan_status(user_id, date.today(), meal_type, 'completed')
            ai_prompt_override = f"오늘의 {meal_type} 식사 기록이 성공적으로 저장되었음을 사용자에게 알리고 격려하는 메시지를 생성해줘."
        else:
            return JSONResponse(content={"message": "어떤 식사를 변경했는지 알려주세요 (예: 아침, 점심, 저녁)."}, status_code=400)
    
    try:
        return StreamingResponse(
            stream_generator(user_profile, message, image_bytes, model, ai_prompt_override),
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
        youtube_query_prompt = f"""From the following text, extract up to **3 keywords** that can be used to search for **YouTube workout routines or specific exercises**.
 
            ✅ [Extract keywords only if at least one of the following conditions is met:]
            🟢 Phrases like "chest workout", "leg workout", "ab workout" (body part + workout type) are included  
            🟢 Specific exercises are mentioned, such as "squat", "bench press", "deadlift", etc.  
            🟢 Mentions of **sets or reps**, like "10 reps", "3 sets", "workout for 10 minutes", etc.  
            🟢 The text contains questions or requests like: "fun workouts", "easy exercises", "beginner workouts"  
            🟢 A **body composition image** (e.g. InBody result) is uploaded, and a workout is requested
 
            ❌ [Return 'None' in the following cases — no exceptions:]
            🔴 Only vague fitness-related words are present, like "workout", "diet", "health", "fitness"  
            🔴 General fitness concepts like "muscle", "physical education", or "running" are mentioned  
            🔴 The text is unrelated to workouts — greetings, chit-chat, or general conversation
 
            ⚠️ [If the user asks for non-workout videos:]
            📛 If a request is made for unrelated videos (e.g. “recommend a funny video”),  
            👉 Just respond with: "Non-workout related videos are not recommended."
 
            📌 Output Format:
            - Return only keywords separated by commas, like: "chest workout, bench press, upper body"
            - If no condition is met, return only 'None'. Do **not** add any explanation or extra text.
 
            Text: '{ai_response}'"""
        
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
