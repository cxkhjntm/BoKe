from datetime import datetime

from pydantic import BaseModel, Field


class ChatSessionCreate(BaseModel):
    title: str = "新会话"


class ChatSessionUpdate(BaseModel):
    title: str


class ChatSessionOut(BaseModel):
    id: int
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1)


class ChatMessagesOut(BaseModel):
    session_id: str
    messages: list[dict]
