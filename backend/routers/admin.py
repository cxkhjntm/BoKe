from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth import get_current_user
from backend.models.user import User
from backend.services import document_service
from backend.utils.response import ok, fail
from backend.utils.logger import get_logger
from backend.exceptions.handlers import AppException

logger = get_logger("routers.admin")
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _require_admin(current_user: User) -> None:
    if not current_user.is_admin:
        raise AppException(code=4003, message="Admin access required", status_code=403)


@router.post("/fts-rebuild")
def rebuild_fts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually rebuild FTS5 index. Admin only."""
    _require_admin(current_user)
    count = document_service.rebuild_fts_index(db)
    return ok(data={"rebuild": True, "document_count": count})
