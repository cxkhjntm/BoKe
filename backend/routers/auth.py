from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.user import LoginRequest, TokenResponse, RefreshRequest, LogoutRequest
from backend.schemas.common import ApiResponse
from backend.services import auth_service
from backend.middleware.auth import get_current_user
from backend.models.user import User
from backend.utils.response import ok, fail
from backend.utils.logger import get_logger

logger = get_logger("routers.auth")
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    result = auth_service.authenticate(db, req.username, req.password)
    return ok(data=result)


@router.post("/refresh")
def refresh_token(req: RefreshRequest, db: Session = Depends(get_db)):
    result = auth_service.refresh(db, req.refresh_token)
    return ok(data=result)


@router.post("/logout")
def logout(
    req: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    auth_service.logout(db, current_user.id, req.refresh_token)
    return ok()
