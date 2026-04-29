from datetime import datetime

from pydantic import BaseModel, Field


class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    expires_days: int = Field(30, ge=1, le=365)


class APIKeyOut(BaseModel):
    id: int
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: datetime | None = None
    created_at: datetime
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}


class APIKeyCreated(BaseModel):
    id: int
    name: str
    key: str  # Only returned once at creation
    key_prefix: str
