"""Tests for document_service (favorites, views, listing filters)."""

import pytest
from backend.services import document_service
from backend.models.user import User
from backend.models.document import Document
from backend.utils.security import hash_password


def _make_user(db):
    user = User(
        username="docuser",
        password_hash=hash_password("pass123"),
        is_admin=False,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_doc(db, user_id, title="Test Doc", file_type="pdf", status="ready", is_favorite=False):
    doc = Document(
        user_id=user_id,
        title=title,
        original_filename=f"{title}.pdf",
        file_type=file_type,
        file_size=1024,
        file_path=f"u{user_id}/{title}.pdf",
        status=status,
        is_favorite=is_favorite,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


class TestToggleFavorite:
    def test_toggle_on(self, db_session):
        user = _make_user(db_session)
        doc = _make_doc(db_session, user.id, is_favorite=False)

        result = document_service.toggle_favorite(db_session, doc.id, user.id)

        assert result.is_favorite is True

    def test_toggle_off(self, db_session):
        user = _make_user(db_session)
        doc = _make_doc(db_session, user.id, is_favorite=True)

        result = document_service.toggle_favorite(db_session, doc.id, user.id)

        assert result.is_favorite is False

    def test_toggle_nonexistent_raises(self, db_session):
        user = _make_user(db_session)

        with pytest.raises(Exception) as exc_info:
            document_service.toggle_favorite(db_session, 99999, user.id)
        assert exc_info.value.status_code == 404

    def test_toggle_other_user_doc_raises(self, db_session):
        user1 = _make_user(db_session)
        user2 = User(
            username="other",
            password_hash=hash_password("pass"),
            is_admin=False,
            is_active=True,
        )
        db_session.add(user2)
        db_session.commit()
        db_session.refresh(user2)
        doc = _make_doc(db_session, user1.id)

        with pytest.raises(Exception) as exc_info:
            document_service.toggle_favorite(db_session, doc.id, user2.id)
        assert exc_info.value.status_code == 404


class TestRecordView:
    def test_increments_view_count(self, db_session):
        user = _make_user(db_session)
        doc = _make_doc(db_session, user.id)

        document_service.record_view(db_session, doc.id, user.id)
        db_session.refresh(doc)
        assert doc.view_count == 1
        assert doc.last_viewed_at is not None

        document_service.record_view(db_session, doc.id, user.id)
        db_session.refresh(doc)
        assert doc.view_count == 2

    def test_nonexistent_doc_no_error(self, db_session):
        user = _make_user(db_session)
        # Should not raise
        document_service.record_view(db_session, 99999, user.id)


class TestListDocumentsFavoriteFilter:
    def test_filter_favorites_only(self, db_session):
        user = _make_user(db_session)
        _make_doc(db_session, user.id, title="Fav1", is_favorite=True)
        _make_doc(db_session, user.id, title="Fav2", is_favorite=True)
        _make_doc(db_session, user.id, title="NotFav", is_favorite=False)

        result = document_service.list_documents(db_session, user.id, is_favorite=True)

        assert result["total"] == 2
        titles = {d.title for d in result["items"]}
        assert titles == {"Fav1", "Fav2"}

    def test_filter_non_favorites(self, db_session):
        user = _make_user(db_session)
        _make_doc(db_session, user.id, title="Fav1", is_favorite=True)
        _make_doc(db_session, user.id, title="NotFav", is_favorite=False)

        result = document_service.list_documents(db_session, user.id, is_favorite=False)

        assert result["total"] == 1
        assert result["items"][0].title == "NotFav"

    def test_no_favorite_filter_returns_all(self, db_session):
        user = _make_user(db_session)
        _make_doc(db_session, user.id, title="Fav1", is_favorite=True)
        _make_doc(db_session, user.id, title="NotFav", is_favorite=False)

        result = document_service.list_documents(db_session, user.id, is_favorite=None)

        assert result["total"] == 2
