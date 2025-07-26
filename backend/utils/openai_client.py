# utils/openai_client.py

import os
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv
import base64
from fastapi import UploadFile
from .ocr import extract_text_from_bytes
from typing import List, Dict
from datetime import date

load_dotenv()

# --- Common Credentials ---
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_API_KEY = os.getenv("AZURE_OPENAI_KEY")

# --- Chat Model Configuration ---
CHAT_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
CHAT_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# --- Embedding Model Configuration ---
EMBEDDING_API_VERSION = os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION")
EMBEDDING_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")

# --- Search Service Configuration ---
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")

# Chat Client Initialization
chat_client = AsyncAzureOpenAI(
    api_key=OPENAI_API_KEY,
    azure_endpoint=OPENAI_ENDPOINT,
    api_version=CHAT_API_VERSION,
    timeout=30.0
)

# Embedding Client Initialization
embedding_client = AsyncAzureOpenAI(
    api_key=OPENAI_API_KEY,
    azure_endpoint=OPENAI_ENDPOINT,
    api_version=EMBEDDING_API_VERSION,
    timeout=30.0
)

async def get_embedding(text: str) -> list[float]:
    response = await embedding_client.embeddings.create(input=text, model=EMBEDDING_DEPLOYMENT_NAME)
    return response.data[0].embedding

async def should_search_long_term_memory(question: str, history: List[Dict]) -> bool:
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history]) if history else "None"

    try:
        response = await chat_client.chat.completions.create(
            model=CHAT_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": f"You are a decision-making assistant. Based on the provided 'Recent Conversation History', determine if the 'User\'s Latest Question' can be answered sufficiently with ONLY this history. If the question is a simple greeting or acknowledgement (e.g., 'Hi', 'Hello', 'Thanks', 'Bye'), answer 'no' regardless of history. If the question involves pronouns (it, that), references past events not in the recent history, or requires deeper knowledge, you must search long-term memory. Answer with only 'yes' (search is needed) or 'no' (search is not needed).\n\n[Recent Conversation History]\n{history_str}"
                },
                {
                    "role": "user",
                    "content": f"[User\'s Latest Question]\n{question}"
                }
            ],
            temperature=0.0,
            max_tokens=5
        )
        decision = response.choices[0].message.content.strip().lower()
        return "yes" in decision
    except Exception as e:
        print(f"장기 기억 검색 여부 판단 오류: {e}")
        return True

async def ask_openai_unified(user_message: str, image_bytes: bytes | None = None, recent_history: List[Dict] = [], rag_history: List[Dict] = []) -> str:
    """단기 기억(recent_history)과 장기 기억(rag_history)을 모두 활용하여 답변을 생성합니다."""
    system_prompt = f"""
'스포츠 지도사 1급' 책과 '헬스의 정석-근력운동'책을 학습해줘.
너는 Gym PT를 도와주는 AI 챗봇이야. 사용자가 인바디 이미지를 업로드할 수 있으며, OCR 텍스트를 참고해서 정확한 분석을 제공해줘.
[과거 검색 기록]이 주어질 경우, 날짜 정보를 참고하여 사용자의 질문에 답변해줘.

사용자가 운동 루틴을 요청하면, 다음 지침을 반드시 따라야 해:
1.  **오늘 날짜({date.today().isoformat()})를 기준으로 루틴을 생성해.** 요일(월, 화, 수) 대신 '1일차', '2일차' 등으로 명확하게 날짜를 기준으로 제시해.
2.  **각 운동에 대해 운동 이름, 세트 수, 횟수를 반드시 포함해.**
3.  **무게(kg)나 시간(분) 정보는 해당 운동에 필요할 경우에만 포함해.** 예를 들어, 덤벨 운동에는 무게를, 플랭크나 달리기에는 시간을 표시해. 맨몸 운동처럼 무게가 필요 없는 경우는 '무게' 항목을 아예 표시하지 마.

사용자가 식단 계획을 요청하면, 다음 지침을 반드시 따라야 해:
1.  **각 식사 항목에 대해 음식 이름, 칼로리, 단백질(g), 탄수화물(g), 지방(g)을 반드시 포함해.** 정확한 수치를 알 수 없는 경우 일반적인 추정치를 제공하거나 '약 N'과 같이 명시하고, **절대 null로 표시하지 마.**

3.  답변을 생성할 때는 [YYYY-MM-DD]와 같은 대괄호 형식으로 날짜를 절대 포함하지 마.
"""
    messages = [{"role": "system", "content": system_prompt}]

    # 컨텍스트 구성 (장기 -> 단기 순으로)
    if rag_history:
        rag_context = "\n".join([f"[{item.get('timestamp').strftime('%Y-%m-%d') if item.get('timestamp') else ''}] {item['role']}: {item['content']}" for item in rag_history])
        messages.append({"role": "system", "content": f"[과거 검색 기록]\n{rag_context}"})

    if recent_history:
        messages.extend(recent_history)

    # 사용자 메시지 및 이미지 처리
    user_content_list = []
    if user_message:
        user_content_list.append({"type": "text", "text": user_message})

    if image_bytes:

        # 1. Azure OCR로 이미지에서 텍스트 추출
        ocr_text = await extract_text_from_bytes(image_bytes)
        if ocr_text:
            ocr_context = f"[Image OCR Result]\n{ocr_text}"
            print(f"--- OCR Result Sent to GPT ---\n{ocr_context}\n------------------------------")
            user_content_list.append({"type": "text", "text": ocr_context})
        
        # 2. 이미지를 Base64로 인코딩하여 AI에게 전달 (Vision 기능)
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        user_content_list.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        })

    messages.append({"role": "user", "content": user_content_list})

    response = await chat_client.chat.completions.create(
        model=CHAT_DEPLOYMENT_NAME,
        messages=messages,
        temperature=0.2,
        max_tokens=2500,
        stream=True,
    )
    return response