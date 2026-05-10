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
        "is_active": config.is_active,
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }


@router.get("")
def get_llm_configs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    configs = db.query(LLMConfig).filter(LLMConfig.user_id == user.id).all()
    if not configs:
        return ok(data=[])
    return ok(data=[_to_out(c) for c in configs])


@router.get("/active")
def get_active_llm_config(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    config = db.query(LLMConfig).filter(
        LLMConfig.user_id == user.id,
        LLMConfig.is_active == 1
    ).first()
    if not config:
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
    config = db.query(LLMConfig).filter(
        LLMConfig.user_id == user.id,
        LLMConfig.provider == body.provider
    ).first()
    
    base_url = LLM_PROVIDER_DEFAULTS.get(body.provider, body.base_url)
    
    # Check if API key is masked (contains ***), if so keep the existing encrypted key
    if config and "***" in body.api_key:
        encrypted_key = config.api_key
    else:
        encrypted_key = encrypt_api_key(body.api_key)
    
    if config:
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
            is_active=0,
        )
        db.add(config)
    db.commit()
    db.refresh(config)
    return ok(data=_to_out(config))


@router.post("/{provider}/activate")
def activate_provider(
    provider: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(LLMConfig).filter(
        LLMConfig.user_id == user.id
    ).update({"is_active": 0})
    
    config = db.query(LLMConfig).filter(
        LLMConfig.user_id == user.id,
        LLMConfig.provider == provider
    ).first()
    if not config:
        raise AppException(code=4004, message="Provider config not found", status_code=404)
    
    config.is_active = 1
    db.commit()
    db.refresh(config)
    return ok(data=_to_out(config))


@router.delete("/{provider}")
def delete_llm_config(
    provider: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    config = db.query(LLMConfig).filter(
        LLMConfig.user_id == user.id,
        LLMConfig.provider == provider
    ).first()
    if config:
        db.delete(config)
        db.commit()
    return ok()
