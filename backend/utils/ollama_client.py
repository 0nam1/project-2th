import ollama
from typing import AsyncGenerator, List, Dict

async def ask_ollama_stream(
    user_message: str,
    recent_history: List[Dict]
) -> AsyncGenerator[str, None]:
    """
    Ollama를 통해 Llama 3.2 모델에 요청하고 응답을 스트리밍합니다.
    """
    messages = recent_history + [{"role": "user", "content": user_message}]
    
    stream = await ollama.AsyncClient().chat(
        model='llama3.2:1b',
        messages=messages,
        stream=True
    )
    
    async for chunk in stream:
        if 'message' in chunk and 'content' in chunk['message']:
            yield chunk['message']['content']
