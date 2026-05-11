from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

_PROVIDER_DEFAULT_BASE_URL = {
    "siliconflow": "https://api.siliconflow.cn/v1",
    "deepseek": "https://api.deepseek.com/v1",
}

# Known providers that have fixed base URLs
_KNOWN_PROVIDERS = set(_PROVIDER_DEFAULT_BASE_URL.keys())


def _is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        host = parsed.hostname or ""
        return len(host) > 0
    except Exception:
        return False


class LLMConfigCreate(BaseModel):
    provider: str
    api_key: str = ""
    base_url: str = ""
    model: str = Field(..., min_length=1)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        if not v:
            return v
        if not _is_valid_url(v):
            raise ValueError("base_url must be a valid HTTP/HTTPS URL")
        return v

    @model_validator(mode="after")
    def fill_base_url(self):
        # For known providers (siliconflow, deepseek), always use default base_url
        if self.provider in _KNOWN_PROVIDERS:
            self.base_url = _PROVIDER_DEFAULT_BASE_URL[self.provider]
        elif not self.base_url or not self.base_url.strip():
            raise ValueError(
                f"Custom provider '{self.provider}' requires a base_url"
            )
        return self


class LLMConfigOut(BaseModel):
    id: int
    provider: str
    api_key: str
    base_url: str
    model: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
