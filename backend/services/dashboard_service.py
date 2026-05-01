"""Dashboard service: statistics, recent views, activity logging."""

import json
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend.models.document import Document
from backend.models.activity import ActivityLog
from backend.utils.logger import get_logger

logger = get_logger("services.dashboard")


def get_stats(db: Session, user_id: int) -> dict:
    """Return document statistics for a user."""
    base = db.query(Document).filter(Document.user_id == user_id)

    total_docs = base.count()
    total_size = db.query(func.sum(Document.file_size)).filter(Document.user_id == user_id).scalar() or 0

    by_type = {}
    for row in (
        db.query(Document.file_type, func.count(Document.id))
        .filter(Document.user_id == user_id)
        .group_by(Document.file_type)
        .all()
    ):
        by_type[row[0]] = row[1]

    by_status = {}
    for row in (
        db.query(Document.status, func.count(Document.id))
        .filter(Document.user_id == user_id)
        .group_by(Document.status)
        .all()
    ):
        by_status[row[0]] = row[1]

    return {
        "total_docs": total_docs,
        "total_size": total_size,
        "by_type": by_type,
        "by_status": by_status,
    }


def get_recent_viewed(db: Session, user_id: int, limit: int = 10) -> list:
    """Return recently viewed documents."""
    return (
        db.query(Document)
        .filter(Document.user_id == user_id, Document.last_viewed_at.isnot(None))
        .order_by(desc(Document.last_viewed_at))
        .limit(limit)
        .all()
    )


def get_top_viewed(db: Session, user_id: int, limit: int = 10) -> list:
    """Return most frequently viewed documents."""
    return (
        db.query(Document)
        .filter(Document.user_id == user_id, Document.view_count > 0)
        .order_by(desc(Document.view_count))
        .limit(limit)
        .all()
    )


def get_activity(db: Session, user_id: int, limit: int = 20) -> list:
    """Return recent activity log entries with document titles."""
    return (
        db.query(ActivityLog, Document.title)
        .outerjoin(Document, ActivityLog.document_id == Document.id)
        .filter(ActivityLog.user_id == user_id)
        .order_by(desc(ActivityLog.created_at))
        .limit(limit)
        .all()
    )


def log_activity(
    db: Session,
    user_id: int,
    action: str,
    document_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    """Write an activity log entry."""
    entry = ActivityLog(
        user_id=user_id,
        document_id=document_id,
        action=action,
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    db.add(entry)
    db.commit()
    logger.debug("Activity logged: user=%d action=%s doc=%s", user_id, action, document_id)
