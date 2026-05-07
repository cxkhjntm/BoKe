from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class LLMConfigCreate(BaseModel):
    provider: str
    api_key: str = Field(..., min_length=10)
    base_url: str
    model: str = Field(..., min_length=1)


class LLMConfigOut(BaseModel):
    id: int
    provider: str
    api_key: str
    base_url: str
    model: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
