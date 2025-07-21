# schemas/chat.py
from pydantic import BaseModel
from typing import Literal, Optional, List

class ChatHistoryCreate(BaseModel):
    user_id: str
    role_type: Literal["user", "assistant", "system"]
    content: str
    embedding: Optional[List[float]] = None
