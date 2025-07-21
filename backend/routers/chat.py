from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from dependencies import get_current_user
from utils.openai_client import (
    ask_openai_unified,
    get_embedding,
    should_search_long_term_memory
)
from crud.chat import (
    save_chat_history, 
    retrieve_and_rerank_history,
    get_recent_chat_history
)
from schemas.chat import ChatHistoryCreate
from typing import Dict, List

router = APIRouter()

# --- 단기 기억 캐시 (In-memory Cache) ---
# { "user_id": [ { "role": ..., "content": ... } ], ... }
chat_cache: Dict[str, List[Dict]] = {}
CACHE_MAX_LENGTH = 10 # 단기 기억으로 저장할 최대 대화 개수

@router.post("/chat/image")
async def chat_with_text_or_image(
    message: str = Form(""),
    image: UploadFile = File(None),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user['user_id']
    rag_history = [] # 장기 기억 검색 결과를 담을 리스트
    embedding = None # 임베딩은 장기 기억 검색 시에만 생성

    try:
        # 1. 단기 기억 조회
        recent_history = chat_cache.get(user_id, [])

        # 2. 장기 기억 검색 여부 판단 (게이트키퍼)
        if await should_search_long_term_memory(message, recent_history):
            print(f"[DEBUG] User({user_id}): 장기 기억 검색 필요. RAG 파이프라인 실행.")
            # --- 깊은 검색 경로 (RAG Pipeline) ---
            # a. 원본 질문을 직접 임베딩
            embedding = await get_embedding(message)
            
            # b. 검색 및 재정렬
            rag_history = await retrieve_and_rerank_history(
                user_id=user_id,
                original_question=message, # 재정렬 시에는 원본 질문을 사용
                transformed_embedding=embedding # 검색 시에는 원본 질문의 임베딩을 사용
            )
        else:
            print(f"[DEBUG] User({user_id}): 단기 기억으로 충분. 빠른 응답 실행.")
            # --- 빠른 경로 (RAG 생략) ---
            # embedding은 None으로 유지

        # 3. 최종 답변 생성
        response = await ask_openai_unified(
            user_message=message,
            image=image,
            recent_history=recent_history,
            rag_history=rag_history
        )

        # 4. 기억 업데이트
        # a. 장기 기억 (DB) 저장
        user_chat_for_db = ChatHistoryCreate(user_id=user_id, role_type="user", content=message, embedding=embedding)
        assistant_chat_for_db = ChatHistoryCreate(user_id=user_id, role_type="assistant", content=response)
        await save_chat_history(user_chat_for_db)
        await save_chat_history(assistant_chat_for_db)

        # b. 단기 기억 (Cache) 업데이트
        if user_id not in chat_cache:
            chat_cache[user_id] = []
        chat_cache[user_id].append({"role": "user", "content": message})
        chat_cache[user_id].append({"role": "assistant", "content": response})
        
        # 캐시 길이 제한
        if len(chat_cache[user_id]) > CACHE_MAX_LENGTH:
            chat_cache[user_id] = chat_cache[user_id][-CACHE_MAX_LENGTH:]

        return {"response": response}

    except Exception as e:
        print(f"채팅 처리 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
