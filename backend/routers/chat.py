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
from ..crud import meal as meal_crud
from ..schemas.chat import ChatHistoryCreate
from ..schemas.plan import WorkoutPlanCreate, DietPlanCreate
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

    출력 형식: {{\"plans\": [{{ \"date\": \"YYYY-MM-DD\", \"type\": \"workout\"/\"diet\", \"items\": [...] }}]}}
    만약 AI 답변이 운동 루틴이나 식단 계획이 아니거나 파싱할 수 없으면, {{\"plans\": []}} 를 반환하세요.
    
    예시 입력 (운동):
    \"1일차: 스쿼트 12회 5세트, 런지 15회 3세트\n2일차: 벤치프레스 10회 5세트 60kg\"
    예시 출력 (운동):
    {{
        \"plans\": [
            {{\"date\": \"{date.today().isoformat()}\", \"type\": \"workout\", \"items\": [
                {{\"exercise_name\": \"스쿼트\", \"reps\": 12, \"sets\": 5, \"weight_kg\": null, \"duration_min\": null}},
                {{\"exercise_name\": \"런지\", \"reps\": 15, \"sets\": 3, \"weight_kg\": null, \"duration_min\": null}}
            ]}},
            {{\"date\": \"{(date.today() + timedelta(days=1)).isoformat()}\", \"type\": \"workout\", \"items\": [
                {{\"exercise_name\": \"벤치프레스\", \"reps\": 10, \"sets\": 5, \"weight_kg\": 60, \"duration_min\": null}}
            ]}}
        ]
    }}

    예시 입력 (식단):
    \"1일차 아침: 닭가슴살 100g, 현미밥 150g\n1일차 점심: 샐러드, 고구마 1개\"
    예시 출력 (식단):
    {{
        \"plans\": [
            {{\"date\": \"{date.today().isoformat()}\", \"type\": \"diet\", \"items\": [
                {{\"meal_type\": \"아침\", \"food_name\": \"닭가슴살\", \"calories\": 165, \"protein_g\": 31.0, \"carbs_g\": 0.0, \"fat_g\": 3.6}},
                {{\"meal_type\": \"아침\", \"food_name\": \"현미밥\", \"calories\": 150, \"protein_g\": 3.0, \"carbs_g\": 32.0, \"fat_g\": 1.0}}
            ]}},
            {{\"date\": \"{date.today().isoformat()}\", \"type\": \"diet\", \"items\": [
                {{\"meal_type\": \"점심\", \"food_name\": \"샐러드\", \"calories\": 50, \"protein_g\": 2.0, \"carbs_g\": 10.0, \"fat_g\": 1.0}},
                {{\"meal_type\": \"점심\", \"food_name\": \"고구마\", \"calories\": 130, \"protein_g\": 2.0, \"carbs_g\": 30.0, \"fat_g\": 0.5}}
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
        print(f"[DEBUG] Parsed data from AI: {parsed_data}") # 디버깅을 위한 출력

        for day_plan in parsed_data.get("plans", []):
            plan_date = date.fromisoformat(day_plan["date"])
            plan_type = day_plan.get("type")

            if plan_type == "workout":
                for exercise in day_plan["items"]:
                    try:
                        # duration_min이 float일 경우를 대비하여 int로 변환
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
                        meal_type = meal.pop("meal_type") # meal_type은 DietPlanCreate에 포함되지 않으므로 분리
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

async def stream_generator(
    user_id: str, user_message: str, image_bytes: bytes | None, model: str, ai_prompt_override: str | None = None
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
        response_stream = ask_ollama_stream(ai_prompt_override if ai_prompt_override else user_message, recent_history)
        async for chunk in response_stream:
            full_response += chunk
            yield chunk
    else:
        response_stream = await ask_openai_unified(ai_prompt_override if ai_prompt_override else user_message, image_bytes, recent_history, rag_history)
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

    # 3. AI 답변이 루틴/식단인지 분석하고 DB에 저장 (백그라운드 실행)
    asyncio.create_task(parse_and_save_plan(user_id, full_response))


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
    if intent == "complete_workout":
        await plan_crud.update_workout_plan_status(user_id, date.today(), 'completed')
        ai_prompt_override = "오늘의 운동을 성공적으로 완료했음을 사용자에게 칭찬하고 격려하는 메시지를 생성해줘."
        image_bytes = await image.read() if image else None
        return StreamingResponse(
            stream_generator(user_id, message, image_bytes, model, ai_prompt_override),
            media_type="text/event-stream"
        )

    elif intent == "modify_workout":
        # TODO: 이 경우, 사용자가 말한 운동으로 오늘 plan을 덮어쓰는 로직 추가 필요
        # 우선은 완료 처리만 함
        await plan_crud.update_workout_plan_status(user_id, date.today(), 'completed')
        ai_prompt_override = "운동 기록이 성공적으로 저장되었음을 사용자에게 알리고 격려하는 메시지를 생성해줘."
        image_bytes = await image.read() if image else None
        return StreamingResponse(
            stream_generator(user_id, message, image_bytes, model, ai_prompt_override),
            media_type="text/event-stream"
        )

    elif intent == "complete_meal":
        meal_type = intent_data.get("meal_type")
        if meal_type:
            await meal_crud.update_diet_plan_status(user_id, date.today(), meal_type, 'completed')
            ai_prompt_override = f"오늘의 {meal_type} 식사를 성공적으로 완료했음을 사용자에게 칭찬하고 격려하는 메시지를 생성해줘."
        else:
            await meal_crud.update_all_diet_plans_status_for_date(user_id, date.today(), 'completed')
            ai_prompt_override = "오늘의 모든 식사를 성공적으로 완료했음을 사용자에게 칭찬하고 격려하는 메시지를 생성해줘."
        image_bytes = await image.read() if image else None
        return StreamingResponse(
            stream_generator(user_id, message, image_bytes, model, ai_prompt_override),
            media_type="text/event-stream"
        )

    elif intent == "modify_meal":
        meal_type = intent_data.get("meal_type")
        if meal_type:
            # TODO: 이 경우, 사용자가 말한 식단으로 오늘 meal plan을 덮어쓰는 로직 추가 필요
            # 우선은 완료 처리만 함
            await meal_crud.update_diet_plan_status(user_id, date.today(), meal_type, 'completed')
            ai_prompt_override = f"오늘의 {meal_type} 식사 기록이 성공적으로 저장되었음을 사용자에게 알리고 격려하는 메시지를 생성해줘."
        else:
            ai_prompt_override = "어떤 식사를 변경했는지 알려주세요 (예: 아침, 점심, 저녁)."
            # 이 경우는 AI 응답이 아니라 고정 메시지이므로, JSONResponse를 유지합니다.
            return JSONResponse(content={"message": ai_prompt_override}, status_code=400)
    
    # 3. 일반 대화 또는 루틴/식단 요청 시, 스트리밍 응답 생성
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
<<<<<<< HEAD
        youtube_query_prompt = f"""
        - [중요]'스포츠 지도사 1급' 책과 '헬스의 정석-근력운동'책을 학습했어
        - 구체적인 운동루틴을 물어보거나, 어떤 운동을 해야하는 질문하는 경우에만 영상을 추출해줘 보여줘.
        - 일반적인 대화로 보는 경우 예를 들어 인사, 대화 등. 운동 종목과 관련되지 않은 키워드가 없는 경우에는 영상을 추출하지 말고. 그냥 답변만 해줘.
        - 운동에서도, 일반 체육 이론의 경우는 영상을 추출하지 말아줘.
        - [중요] 인바디 체성분 분석 이미지를 올려서 답변을 요청한 경우에는 운동 루틴 영상을 추출해줘야해!
        - '부위'+'운동'은 무조건 운동 방법을 알려주는 경우니까 유튜브 영상 추출해줘.
        - 단순히 '근육', '체육', '달리기'를 물어보는 것에 대해 유튜브 영상 추출하지 말아줘.
        - 답변에 운동 종목, 운동 횟수가 포함된 경우에는 유튜브 영상 추출해줘.
        - [중요] 단순 영상 요청이나, 운동과 관련없는 영상 요청의 경우 "운동과 관련되지 않은 영상은 추천되지 않습니다." 메시지로 답변해줘.
        - 그럼에도 '재밌는 운동 알려줘'와 유사한 질문에는 체육관 운동 영상으로 추천해줘.
        - 다음 텍스트에서 YouTube에서 검색할 운동 루틴, 운동 종목 관련 키워드를 3개 이내로 추출해줘. 텍스트가 운동 루틴과 관련이 없다면 'None'이라고만 답변해줘. 텍스트: '{ai_response}'
        """
=======
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
>>>>>>> main
        
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