from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DocumentStatus = Literal["queued", "processing", "ready", "error"]
DocumentCategory = Literal["sujian", "shicui", "manbi"]

CATEGORY_LABELS: dict[str, str] = {
    "sujian": "素笺",
    "shicui": "拾萃",
    "manbi": "漫笔",
}


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
    is_favorite: bool = False
    category: DocumentCategory | None = None
    view_count: int = 0
    last_viewed_at: datetime | None = None
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
    is_favorite: bool = False
    category: DocumentCategory | None = None
    view_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUpdate(BaseModel):
    title: str = Field(None, min_length=1, max_length=255)


class CategoryUpdate(BaseModel):
    category: DocumentCategory | None = None


class CategoryInfo(BaseModel):
    code: str
    label: str


class TimelineResponse(BaseModel):
    groups: dict[str, list[DocumentListItem]]
    next_before: str | None = None
    has_more: bool = False
