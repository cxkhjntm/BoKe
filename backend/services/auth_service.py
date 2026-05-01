from datetime import datetime, timedelta
import threading

from sqlalchemy.orm import Session

from backend.models.user import User
from backend.models.refresh_token import RefreshToken
from backend.utils.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from backend.utils.logger import get_logger
from backend.exceptions.handlers import AppException
from backend.config import ADMIN_USERNAME, ADMIN_PASSWORD

# Lock to serialize refresh token rotation within the same process.
# Prevents concurrent requests from reusing the same refresh token.
_refresh_lock = threading.Lock()

logger = get_logger("services.auth")

MAX_LOGIN_FAILURES = 10
LOCKOUT_MINUTES = 15


def init_admin(db: Session) -> None:
    """Create default admin user if not exists."""
    existing = db.query(User).filter(User.username == ADMIN_USERNAME).first()
    if existing:
        return
    from backend.utils.security import hash_password

    admin = User(
        username=ADMIN_USERNAME,
        password_hash=hash_password(ADMIN_PASSWORD),
        is_admin=True,
    )
    db.add(admin)
    db.commit()
    logger.info("Admin user '%s' created.", ADMIN_USERNAME)


def authenticate(db: Session, username: str, password: str) -> dict:
    """Authenticate user and return tokens. Raises AppException on failure."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise AppException(code=4001, message="Invalid username or password", status_code=401)

    # Check account lockout (naive UTC to match SQLite storage)
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = int((user.locked_until - datetime.utcnow()).total_seconds() / 60)
        raise AppException(
            code=4030,
            message=f"Account is locked. Try again in {remaining} minutes.",
            status_code=423,
        )

    # Reset failure count if lockout has expired (prevents re-lock on first post-lockout failure)
    if user.locked_until and user.locked_until <= datetime.utcnow():
        user.login_failures = 0
        user.locked_until = None

    if not verify_password(password, user.password_hash):
        # Increment failure count
        user.login_failures = (user.login_failures or 0) + 1
        if user.login_failures >= MAX_LOGIN_FAILURES:
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
            logger.warning("Account '%s' locked due to %d failed attempts.", username, MAX_LOGIN_FAILURES)
        db.commit()
        raise AppException(code=4001, message="Invalid username or password", status_code=401)

    # Reset failure count on success
    user.login_failures = 0
    user.locked_until = None
    db.commit()

    # Create tokens
    access_token, _ = create_access_token(user.id)
    refresh_token, jti, expires_at = create_refresh_token(user.id)

    # Store refresh token
    rt = RefreshToken(user_id=user.id, jti=jti, expires_at=expires_at)
    db.add(rt)
    db.commit()

    logger.info("User '%s' logged in.", username)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


def refresh(db: Session, refresh_token_str: str) -> dict:
    """Refresh access token. Implements token rotation with concurrency-safe locking."""
    try:
        payload = decode_token(refresh_token_str)
    except Exception:
        raise AppException(code=4001, message="Invalid refresh token", status_code=401)

    if payload.get("type") != "refresh":
        raise AppException(code=4001, message="Invalid token type", status_code=401)

    jti = payload.get("jti")
    user_id = int(payload.get("sub"))

    # Serialize refresh token rotation to prevent concurrent requests from
    # reusing the same refresh token. The lock ensures the read-check-revoke
    # sequence is atomic within this process.
    with _refresh_lock:
        rt = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
        if not rt:
            # Token family detection: if a revoked token is reused, revoke all user tokens
            logger.warning("Possible token reuse detected for user %d. Revoking all tokens.", user_id)
            db.query(RefreshToken).filter(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False,
            ).update({"revoked": True})
            db.commit()
            raise AppException(code=4001, message="Refresh token has been revoked", status_code=401)

        if rt.revoked:
            # Token family detection
            logger.warning("Revoked refresh token reused for user %d. Revoking all tokens.", user_id)
            db.query(RefreshToken).filter(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False,
            ).update({"revoked": True})
            db.commit()
            raise AppException(code=4001, message="Refresh token has been revoked", status_code=401)

        # Revoke old refresh token (rotation)
        rt.revoked = True

        # Create new tokens
        new_access, _ = create_access_token(user_id)
        new_refresh, new_jti, new_expires = create_refresh_token(user_id)

        new_rt = RefreshToken(user_id=user_id, jti=new_jti, expires_at=new_expires)
        db.add(new_rt)
        db.commit()

    logger.info("Tokens refreshed for user %d.", user_id)
    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


def logout(db: Session, user_id: int, refresh_token_str: str) -> None:
    """Revoke the given refresh token."""
    try:
        payload = decode_token(refresh_token_str)
        jti = payload.get("jti")
        if jti:
            rt = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
            if rt:
                rt.revoked = True
                db.commit()
                logger.info("Refresh token revoked for user %d.", user_id)
    except Exception:
        logger.warning("Failed to decode refresh token during logout for user %d.", user_id)
