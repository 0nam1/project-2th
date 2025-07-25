import asyncio # asyncio 임포트 추가
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, JSONResponse
from dependencies import get_current_user
from utils.openai_client import (
    ask_openai_unified,
    get_embedding,
    should_search_long_term_memory,
    chat_client,
    CHAT_DEPLOYMENT_NAME
)
from utils.ollama_client import ask_ollama_stream
from crud.chat import (
    save_chat_history,
    retrieve_and_rerank_history
)
from schemas.chat import ChatHistoryCreate
from typing import Dict, List, AsyncGenerator
from utils.youtube_search import search_youtube_videos
import json

router = APIRouter()

# --- 단기 기억 캐시 (In-memory Cache) ---
chat_cache: Dict[str, List[Dict]] = {}
CACHE_MAX_LENGTH = 10

async def stream_generator(
    user_id: str,
    user_message: str,
    image_bytes: bytes | None,
    recent_history: List[Dict],
    rag_history: List[Dict],
    embedding: List[float] | None,
    model: str
) -> AsyncGenerator[str, None]:
    
    full_response = ""
    
    if model == "llama3.2:1b":
        # Ollama는 이미지 입력을 지원하지 않으므로 텍스트만 사용
        response_stream = ask_ollama_stream(
            user_message=user_message,
            recent_history=recent_history
        )
        async for chunk in response_stream:
            full_response += chunk
            yield chunk
    else: # 기본값은 OpenAI
        response_stream = await ask_openai_unified(
            user_message=user_message,
            image_bytes=image_bytes,
            recent_history=recent_history,
            rag_history=rag_history
        )
        async for chunk in response_stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                for char in content: # 각 문자를 개별적으로 yield
                    full_response += char
                    yield char
                    await asyncio.sleep(0.01) # 작은 지연 추가 (예: 50ms)

    print(f"[DEBUG] Full AI Response from {model}: {full_response}")

    # 스트리밍 종료 후 DB 및 캐시 업데이트
    user_chat_for_db = ChatHistoryCreate(user_id=user_id, role_type="user", content=user_message, embedding=embedding)
    assistant_chat_for_db = ChatHistoryCreate(user_id=user_id, role_type="assistant", content=full_response)
    await save_chat_history(user_chat_for_db)
    await save_chat_history(assistant_chat_for_db)

    if user_id not in chat_cache:
        chat_cache[user_id] = []
    chat_cache[user_id].append({"role": "user", "content": user_message})
    chat_cache[user_id].append({"role": "assistant", "content": full_response})
    
    if len(chat_cache[user_id]) > CACHE_MAX_LENGTH:
        chat_cache[user_id] = chat_cache[user_id][-CACHE_MAX_LENGTH:]

@router.post("/chat/image")
async def chat_with_text_or_image(
    message: str = Form(""),
    image: UploadFile = File(None),
    model: str = Form("gpt-4o"), # 모델 선택 파라미터 추가
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user['user_id']
    rag_history = []
    embedding = None

    try:
        image_bytes = await image.read() if image else None
        recent_history = chat_cache.get(user_id, [])

        # Llama3.2는 RAG 및 이미지 검색을 지원하지 않으므로, OpenAI 모델 사용 시에만 실행
        if model == "gpt-4o":
            if await should_search_long_term_memory(message, recent_history):
                embedding = await get_embedding(message)
                rag_history = await retrieve_and_rerank_history(
                    user_id=user_id,
                    original_question=message,
                    transformed_embedding=embedding
                )
            if embedding is None and message:
                embedding = await get_embedding(message)
        
        return StreamingResponse(
            stream_generator(user_id, message, image_bytes, recent_history, rag_history, embedding, model),
            media_type="text/event-stream"
        )

    except Exception as e:
        print(f"채팅 처리 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

@router.get("/youtube_search")
async def get_youtube_videos(
    ai_response: str = Query(..., alias="query", min_length=1), # AI 답변을 query 파라미터로 받음
    max_results: int = Query(3, ge=1, le=10),
    current_user: dict = Depends(get_current_user)
):
    try:
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
            return JSONResponse(content=[], status_code=200) # 키워드 없으면 빈 리스트 반환

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")