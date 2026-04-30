"""Tests for dashboard_service (stats, recent, top, activity)."""

import pytest
from datetime import datetime, timedelta

from backend.services import dashboard_service, document_service
from backend.models.user import User
from backend.models.document import Document
from backend.models.activity import ActivityLog
from backend.utils.security import hash_password


def _make_user(db):
    user = User(
        username="dashuser",
        password_hash=hash_password("pass123"),
        is_admin=False,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_doc(db, user_id, title="Test", file_type="pdf", status="ready", view_count=0, last_viewed_at=None):
    doc = Document(
        user_id=user_id,
        title=title,
        original_filename=f"{title}.pdf",
        file_type=file_type,
        file_size=1024,
        file_path=f"u{user_id}/{title}.pdf",
        status=status,
        view_count=view_count,
        last_viewed_at=last_viewed_at,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


class TestGetStats:
    def test_empty_stats(self, db_session):
        user = _make_user(db_session)
        stats = dashboard_service.get_stats(db_session, user.id)

        assert stats["total_docs"] == 0
        assert stats["total_size"] == 0
        assert stats["by_type"] == {}
        assert stats["by_status"] == {}

    def test_stats_with_documents(self, db_session):
        user = _make_user(db_session)
        _make_doc(db_session, user.id, title="A", file_type="pdf", status="ready")
        _make_doc(db_session, user.id, title="B", file_type="docx", status="ready")
        _make_doc(db_session, user.id, title="C", file_type="pdf", status="queued")

        stats = dashboard_service.get_stats(db_session, user.id)

        assert stats["total_docs"] == 3
        assert stats["total_size"] == 3 * 1024
        assert stats["by_type"] == {"pdf": 2, "docx": 1}
        assert stats["by_status"] == {"ready": 2, "queued": 1}


class TestGetRecentViewed:
    def test_returns_sorted_by_last_viewed(self, db_session):
        user = _make_user(db_session)
        now = datetime.utcnow()
        d1 = _make_doc(db_session, user.id, title="Old", last_viewed_at=now - timedelta(hours=2))
        d2 = _make_doc(db_session, user.id, title="New", last_viewed_at=now - timedelta(minutes=5))
        _make_doc(db_session, user.id, title="Never")  # no last_viewed_at

        result = dashboard_service.get_recent_viewed(db_session, user.id)

        assert len(result) == 2
        assert result[0].title == "New"
        assert result[1].title == "Old"


class TestGetTopViewed:
    def test_returns_sorted_by_view_count(self, db_session):
        user = _make_user(db_session)
        _make_doc(db_session, user.id, title="Popular", view_count=50)
        _make_doc(db_session, user.id, title="Less", view_count=5)
        _make_doc(db_session, user.id, title="Zero")  # view_count=0

        result = dashboard_service.get_top_viewed(db_session, user.id)

        assert len(result) == 2
        assert result[0].title == "Popular"
        assert result[1].title == "Less"


class TestLogActivity:
    def test_log_creates_entry(self, db_session):
        user = _make_user(db_session)
        doc = _make_doc(db_session, user.id)

        dashboard_service.log_activity(db_session, user.id, "view", doc.id)

        entries = db_session.query(ActivityLog).all()
        assert len(entries) == 1
        assert entries[0].action == "view"
        assert entries[0].document_id == doc.id
        assert entries[0].user_id == user.id

    def test_log_with_metadata(self, db_session):
        user = _make_user(db_session)

        dashboard_service.log_activity(db_session, user.id, "search", metadata={"query": "test"})

        entries = db_session.query(ActivityLog).all()
        assert len(entries) == 1
        assert entries[0].action == "search"
        assert '"query"' in entries[0].metadata_json


class TestGetActivity:
    def test_returns_recent_activities(self, db_session):
        user = _make_user(db_session)
        dashboard_service.log_activity(db_session, user.id, "upload")
        dashboard_service.log_activity(db_session, user.id, "view")
        dashboard_service.log_activity(db_session, user.id, "search")

        result = dashboard_service.get_activity(db_session, user.id)

        assert len(result) == 3
        assert result[0].action == "search"  # most recent first
        assert result[2].action == "upload"

    def test_respects_limit(self, db_session):
        user = _make_user(db_session)
        for i in range(5):
            dashboard_service.log_activity(db_session, user.id, "view")

        result = dashboard_service.get_activity(db_session, user.id, limit=3)

        assert len(result) == 3
