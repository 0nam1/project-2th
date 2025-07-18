# utils/openai_client.py

import os
from openai import AzureOpenAI
from dotenv import load_dotenv
import base64
from fastapi import UploadFile
from utils.ocr import extract_text_from_uploadfile

load_dotenv()

OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")   # https://xxx.openai.azure.com
OPENAI_API_KEY = os.getenv("AZURE_OPENAI_KEY")
DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")  # gpt-4o
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")  # 2025-01-01-preview

# Azure OpenAI 클라이언트 초기화
client = AzureOpenAI(
    api_key=OPENAI_API_KEY,
    azure_endpoint=OPENAI_ENDPOINT,
    api_version=API_VERSION
)

from utils.ocr import extract_text_from_uploadfile  # OCR 함수 불러오기

async def ask_openai_unified(user_message: str, image: UploadFile | None = None) -> str:
    """
    이미지가 있으면 Azure OCR로 텍스트 추출 후 GPT에 함께 전달
    """
    user_content = []

    # 1. OCR 텍스트 추출
    ocr_text = ""
    if image:
        try:
            ocr_text = await extract_text_from_uploadfile(image)
        except Exception as e:
            print("OCR 처리 실패:", e)
            ocr_text = ""

    # 2. 사용자 메시지 구성
    if user_message:
        user_content.append({"type": "text", "text": user_message})

    # 3. OCR 텍스트 추가
    if ocr_text:
        print(ocr_text)
        user_content.append({
            "type": "text",
            "text": f"[OCR로 추출된 인바디 텍스트]\n{ocr_text}"
        })

    # 4. 이미지 base64 처리
    if image:
        image.file.seek(0)  # OCR 후 파일 포인터 초기화
        image_bytes = await image.read()
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        content_type = image.content_type or "image/jpeg"
        user_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{content_type};base64,{encoded_image}"
            }
        })

    # GPT 요청
    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": [
                        {"type": "text", "text": "너는 Gym PT를 도와주는 AI 챗봇이야. 사용자가 인바디 이미지를 업로드할 수 있으며, OCR 텍스트를 참고해서"
                                                 "정확한 분석을 제공해줘."}
                    ]
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            temperature=0.7,
            max_tokens=1200,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
        )
        print(response.choices[0].message.content)
        return response.choices[0].message.content

    except Exception as e:
        print("Azure OpenAI 호출 오류:", e)
        raise