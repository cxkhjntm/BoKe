from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth import get_current_user
from backend.models.user import User
from backend.models.api_key import APIKey
from backend.schemas.api_key import APIKeyCreate, APIKeyOut, APIKeyCreated
from backend.utils.response import ok
from backend.utils.security import generate_api_key
from backend.utils.logger import get_logger
from backend.exceptions.handlers import AppException

logger = get_logger("routers.api_keys")
router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


@router.get("")
def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()
    items = [APIKeyOut.model_validate(k).model_dump() for k in keys]
    return ok(data={"items": items})


@router.post("")
def create_api_key(
    body: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raw_key, key_hash, key_prefix = generate_api_key()

    from datetime import datetime, timedelta, timezone

    api_key = APIKey(
        user_id=current_user.id,
        name=body.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        expires_at=datetime.now(timezone.utc) + timedelta(days=body.expires_days),
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    logger.info("API key created: id=%d, name='%s'", api_key.id, body.name)
    return ok(data={
        "id": api_key.id,
        "name": api_key.name,
        "key": raw_key,
        "key_prefix": key_prefix,
    })


@router.delete("/{key_id}")
def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id,
    ).first()
    if not api_key:
        raise AppException(code=4004, message="API key not found", status_code=404)

    db.delete(api_key)
    db.commit()
    logger.info("API key deleted: id=%d", key_id)
    return ok()
