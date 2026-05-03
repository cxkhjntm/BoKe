from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt

from backend.database import get_db
from backend.models.user import User
from backend.models.api_key import APIKey
from backend.utils.security import decode_token, sha256_hash
from backend.utils.logger import get_logger

logger = get_logger("middleware.auth")
security = HTTPBearer(auto_error=False)


def _client_ip(request: Request = None) -> str:
    if not request:
        return "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Authenticate via Authorization header (JWT or API Key)."""
    if not credentials:
        logger.warning("Auth failed: no credentials provided (ip=%s)", _client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "Authentication required", "data": None},
        )
    token = credentials.credentials
    if token.startswith("sk-"):
        return _authenticate_api_key(token, db, request)
    return _authenticate_jwt(token, db, request)


def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Like get_current_user but returns None instead of raising when credentials are missing."""
    if not credentials:
        return None
    token = credentials.credentials
    if token.startswith("sk-"):
        return _authenticate_api_key(token, db, request)
    return _authenticate_jwt(token, db, request)


def authenticate_from_token(token: str, db: Session, request: Request = None) -> User:
    """Authenticate from a raw token string (used for query-param auth in file endpoints)."""
    if token.startswith("sk-"):
        return _authenticate_api_key(token, db, request)
    return _authenticate_jwt(token, db, request)


def _authenticate_jwt(token: str, db: Session, request: Request = None) -> User:
    """Authenticate via JWT Bearer token."""
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        logger.warning("Auth failed: token expired (ip=%s)", _client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "Token has expired", "data": None},
        )
    except jwt.InvalidTokenError:
        logger.warning("Auth failed: invalid token (ip=%s)", _client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "Invalid token", "data": None},
        )

    if payload.get("type") != "access":
        logger.warning("Auth failed: wrong token type (ip=%s)", _client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "Invalid token type", "data": None},
        )

    user_id = payload.get("sub")
    if not user_id:
        logger.warning("Auth failed: missing sub claim (ip=%s)", _client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "Invalid token payload", "data": None},
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        logger.warning("Auth failed: user %s not found or inactive (ip=%s)", user_id, _client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "User not found or inactive", "data": None},
        )

    return user


def _authenticate_api_key(key: str, db: Session, request: Request = None) -> User:
    """Authenticate via API Key (sk-xxx)."""
    key_hash = sha256_hash(key)

    api_key = db.query(APIKey).filter(APIKey.key_hash == key_hash).first()
    if not api_key:
        logger.warning("Auth failed: invalid API key (ip=%s)", _client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "Invalid API key", "data": None},
        )

    if not api_key.is_active:
        logger.warning("Auth failed: API key inactive (key_id=%d, ip=%s)", api_key.id, _client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "API key is inactive", "data": None},
        )

    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        logger.warning("Auth failed: API key expired (key_id=%d, ip=%s)", api_key.id, _client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "API key has expired", "data": None},
        )

    user = db.query(User).filter(User.id == api_key.user_id).first()
    if not user or not user.is_active:
        logger.warning("Auth failed: API key user not found or inactive (key_id=%d, ip=%s)", api_key.id, _client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "User not found or inactive", "data": None},
        )

    # Update last_used_at
    api_key.last_used_at = datetime.utcnow()
    db.commit()

    logger.info("API key auth success: key_id=%d, user_id=%d", api_key.id, user.id)
    return user
