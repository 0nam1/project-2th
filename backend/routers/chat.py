from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from dependencies import get_current_user
from utils.openai_client import ask_openai_unified  # ✅ 통합 함수만 사용

router = APIRouter()

@router.post("/chat/image")
async def chat_with_text_or_image(
    message: str = Form(""),
    image: UploadFile = File(None),
    current_user: dict = Depends(get_current_user)
):
    try:
        response = await ask_openai_unified(message, image)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))