from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth import get_current_user
from backend.models.user import User
from backend.models.llm_config import LLMConfig
from backend.config import LLM_PROVIDER_DEFAULTS
from backend.schemas.llm_config import LLMConfigCreate, LLMConfigOut
from backend.utils.response import ok
from backend.utils.crypto_utils import encrypt_api_key, decrypt_api_key
from backend.exceptions.handlers import AppException

router = APIRouter(prefix="/api/v1/llm-config", tags=["LLM Config"])


def _mask_api_key(key: str) -> str:
    if len(key) < 12:
        return "***"
    return key[:8] + "***" + key[-4:]


def _to_out(config: LLMConfig) -> dict:
    return {
        "id": config.id,
        "provider": config.provider,
        "api_key": _mask_api_key(config.api_key),
        "base_url": config.base_url,
        "model": config.model,
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }


@router.get("")
def get_llm_config(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    config = db.query(LLMConfig).filter(LLMConfig.user_id == user.id).first()
    if not config:
        return ok(data=None)
    return ok(data=_to_out(config))


@router.post("")
def upsert_llm_config(
    body: LLMConfigCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    config = db.query(LLMConfig).filter(LLMConfig.user_id == user.id).first()
    encrypted_key = encrypt_api_key(body.api_key)
    base_url = body.base_url or LLM_PROVIDER_DEFAULTS.get(body.provider, "")
    if config:
        config.provider = body.provider
        config.api_key = encrypted_key
        config.base_url = base_url
        config.model = body.model
    else:
        config = LLMConfig(
            user_id=user.id,
            provider=body.provider,
            api_key=encrypted_key,
            base_url=base_url,
            model=body.model,
        )
        db.add(config)
    db.commit()
    db.refresh(config)
    return ok(data=_to_out(config))


@router.delete("")
def delete_llm_config(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    config = db.query(LLMConfig).filter(LLMConfig.user_id == user.id).first()
    if config:
        db.delete(config)
        db.commit()
    return ok()
