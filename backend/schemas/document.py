from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DocumentStatus = Literal["queued", "processing", "ready", "error"]


class DocumentOut(BaseModel):
    id: int
    title: str
    original_filename: str
    file_type: str
    file_size: int
    file_path: str | None = None
    thumbnail_path: str | None = None
    content_text: str | None = None
    status: DocumentStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListItem(BaseModel):
    id: int
    title: str
    original_filename: str
    file_type: str
    file_size: int
    thumbnail_path: str | None = None
    status: DocumentStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUpdate(BaseModel):
    title: str = Field(None, min_length=1, max_length=255)
