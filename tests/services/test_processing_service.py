"""Tests for backend.services.processing_service."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend.services import processing_service
from backend.models.document import Document


class TestProcessDocument:
    def _make_user(self, db_session):
        from backend.models.user import User
        from backend.utils.security import hash_password
        user = User(
            username="procuser",
            password_hash=hash_password("pass"),
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    def _make_doc(self, db_session, user_id=None, file_type="pdf", file_path="1/original/test.pdf"):
        if user_id is None:
            user_id = self._make_user(db_session).id
        doc = Document(
            user_id=user_id,
            title="Test",
            original_filename="test.pdf",
            file_type=file_type,
            file_size=100,
            file_path=file_path,
            status="queued",
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        return doc

    def test_missing_file_sets_error(self, db_session, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.services.processing_service.STORAGE_PATH", tmp_path)
        doc = self._make_doc(db_session)

        processing_service.process_document(db_session, doc)

        assert doc.status == "error"
        assert "not found" in (doc.error_message or "").lower()

    def test_success_pdf(self, db_session, tmp_path, sample_pdf, monkeypatch):
        monkeypatch.setattr("backend.services.processing_service.STORAGE_PATH", tmp_path)
        # Copy sample PDF into expected location
        dest = tmp_path / "1" / "original"
        dest.mkdir(parents=True)
        pdf_file = dest / "test.pdf"
        pdf_file.write_bytes(sample_pdf.read_bytes())

        doc = self._make_doc(db_session, file_path="1/original/test.pdf")
        processing_service.process_document(db_session, doc)

        assert doc.status == "ready"
        assert doc.content_text is not None
        assert "Hello" in doc.content_text

    def test_both_steps_fail_sets_error(self, db_session, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.services.processing_service.STORAGE_PATH", tmp_path)
        dest = tmp_path / "1" / "original"
        dest.mkdir(parents=True)
        (dest / "bad.pdf").write_bytes(b"not a real pdf")

        doc = self._make_doc(db_session, file_path="1/original/bad.pdf")
        # Force both extraction and thumbnail to fail by patching
        with patch("backend.services.processing_service.extract_service.extract_text", side_effect=Exception("fail")), \
             patch("backend.services.processing_service.thumbnail_service.generate_thumbnail", return_value=None):
            processing_service.process_document(db_session, doc)

        assert doc.status == "error"

    def test_partial_success_text_only(self, db_session, tmp_path, sample_pdf, monkeypatch):
        monkeypatch.setattr("backend.services.processing_service.STORAGE_PATH", tmp_path)
        dest = tmp_path / "1" / "original"
        dest.mkdir(parents=True)
        pdf_file = dest / "test.pdf"
        pdf_file.write_bytes(sample_pdf.read_bytes())

        doc = self._make_doc(db_session, file_path="1/original/test.pdf")
        with patch("backend.services.processing_service.thumbnail_service.generate_thumbnail", return_value=None):
            processing_service.process_document(db_session, doc)

        # Text extraction succeeds, thumbnail fails → still "ready"
        assert doc.status == "ready"
        assert doc.content_text is not None


class TestRetryProcessing:
    def test_resets_state_and_reprocesses(self, db_session, tmp_path, sample_pdf, monkeypatch):
        monkeypatch.setattr("backend.services.processing_service.STORAGE_PATH", tmp_path)
        dest = tmp_path / "1" / "original"
        dest.mkdir(parents=True)
        pdf_file = dest / "test.pdf"
        pdf_file.write_bytes(sample_pdf.read_bytes())

        from backend.models.user import User
        from backend.utils.security import hash_password
        user = User(username="retryuser", password_hash=hash_password("pass"), is_active=True)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        doc = Document(
            user_id=user.id,
            title="Test",
            original_filename="test.pdf",
            file_type="pdf",
            file_size=100,
            file_path="1/original/test.pdf",
            status="error",
            error_message="previous failure",
            content_text=None,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        processing_service.retry_processing(db_session, doc)

        assert doc.status == "ready"
        assert doc.error_message is None
