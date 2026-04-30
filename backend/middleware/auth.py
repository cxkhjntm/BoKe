from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt

from backend.database import get_db
from backend.models.user import User
from backend.models.api_key import APIKey
from backend.utils.security import decode_token, sha256_hash
from backend.utils.logger import get_logger

logger = get_logger("middleware.auth")
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials

    # Route to API key auth if token has the sk- prefix
    if token.startswith("sk-"):
        return _authenticate_api_key(token, db)

    return _authenticate_jwt(token, db)


def _authenticate_jwt(token: str, db: Session) -> User:
    """Authenticate via JWT Bearer token."""
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "Token has expired", "data": None},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "Invalid token", "data": None},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "Invalid token type", "data": None},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "Invalid token payload", "data": None},
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "User not found or inactive", "data": None},
        )

    return user


def _authenticate_api_key(key: str, db: Session) -> User:
    """Authenticate via API Key (sk-xxx)."""
    key_hash = sha256_hash(key)

    api_key = db.query(APIKey).filter(APIKey.key_hash == key_hash).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "Invalid API key", "data": None},
        )

    if not api_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "API key is inactive", "data": None},
        )

    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "API key has expired", "data": None},
        )

    user = db.query(User).filter(User.id == api_key.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "User not found or inactive", "data": None},
        )

    # Update last_used_at
    api_key.last_used_at = datetime.utcnow()
    db.commit()

    logger.info("API key auth success: key_id=%d, user_id=%d", api_key.id, user.id)
    return user
