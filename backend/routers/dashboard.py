"""Dashboard API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth import get_current_user
from backend.models.user import User
from backend.schemas.document import DocumentListItem
from backend.services import dashboard_service
from backend.utils.response import ok

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/stats")
def stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = dashboard_service.get_stats(db, current_user.id)
    return ok(data=data)


@router.get("/recent")
def recent_viewed(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    docs = dashboard_service.get_recent_viewed(db, current_user.id, limit)
    items = [DocumentListItem.model_validate(d).model_dump() for d in docs]
    return ok(data=items)


@router.get("/top")
def top_viewed(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    docs = dashboard_service.get_top_viewed(db, current_user.id, limit)
    items = [DocumentListItem.model_validate(d).model_dump() for d in docs]
    return ok(data=items)


@router.get("/activity")
def activity(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entries = dashboard_service.get_activity(db, current_user.id, limit)
    items = [
        {
            "id": e.id,
            "action": e.action,
            "document_id": e.document_id,
            "metadata": e.metadata_json,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]
    return ok(data=items)
