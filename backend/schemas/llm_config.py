from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

_ALLOWED_HOSTS = {
    "siliconflow.cn",
    "api.siliconflow.cn",
    "deepseek.com",
    "api.deepseek.com",
}


def _is_allowed_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        host = parsed.hostname or ""
        return any(
            host == allowed or host.endswith(f".{allowed}")
            for allowed in _ALLOWED_HOSTS
        )
    except Exception:
        return False


class LLMConfigCreate(BaseModel):
    provider: str
    api_key: str = Field(..., min_length=10)
    base_url: str
    model: str = Field(..., min_length=1)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        if not _is_allowed_url(v):
            raise ValueError("base_url must be a SiliconFlow or DeepSeek API endpoint")
        return v


class LLMConfigOut(BaseModel):
    id: int
    provider: str
    api_key: str
    base_url: str
    model: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
