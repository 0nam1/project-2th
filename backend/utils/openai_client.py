# utils/openai_client.py

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")   # https://xxx.openai.azure.com
OPENAI_API_KEY = os.getenv("AZURE_OPENAI_KEY")
DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")  # gpt-4o
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")  # 2025-01-01-preview

async def ask_openai(user_message: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "api-key": OPENAI_API_KEY,
    }

    payload = {
        "messages": [
            {"role": "system", "content": "너는 Gym PT를 도와주는 AI 챗봇이야."},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.7,
        "max_tokens": 1000,
        "top_p": 0.95,
        "frequency_penalty": 0,
        "presence_penalty": 0,
    }

    url = f"{OPENAI_ENDPOINT}/openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version={API_VERSION}"

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"]["content"]