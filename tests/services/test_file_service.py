"""Tests for backend.services.file_service."""

import pytest
from pathlib import Path

from backend.services import file_service


class TestGetUserStorage:
    def test_creates_directory_structure(self, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.services.file_service.STORAGE_PATH", tmp_path)
        user_dir = file_service.get_user_storage(42)

        assert user_dir == tmp_path / "42"
        assert (user_dir / "original").is_dir()
        assert (user_dir / "processed").is_dir()
        assert (user_dir / "thumbnails").is_dir()

    def test_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.services.file_service.STORAGE_PATH", tmp_path)
        d1 = file_service.get_user_storage(1)
        d2 = file_service.get_user_storage(1)
        assert d1 == d2


class TestSaveFile:
    def test_returns_relative_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.services.file_service.STORAGE_PATH", tmp_path)
        rel = file_service.save_file(1, "test.txt", b"hello world")

        assert rel.startswith("1/original/")
        assert rel.endswith(".txt")
        assert (tmp_path / rel).exists()
        assert (tmp_path / rel).read_bytes() == b"hello world"

    def test_uuid_filename(self, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.services.file_service.STORAGE_PATH", tmp_path)
        rel1 = file_service.save_file(1, "a.pdf", b"x")
        rel2 = file_service.save_file(1, "a.pdf", b"y")

        assert rel1 != rel2  # UUID ensures uniqueness

    def test_subfolder_respected(self, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.services.file_service.STORAGE_PATH", tmp_path)
        rel = file_service.save_file(1, "out.txt", b"data", subfolder="processed")

        assert "processed" in rel
        assert (tmp_path / rel).exists()

    def test_path_traversal_via_subfolder(self, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.services.file_service.STORAGE_PATH", tmp_path)
        # The UUID neutralizes filename traversal, but subfolder is passed directly
        # Need enough ../ to escape tmp_path entirely (user dir is tmp_path/1/)
        with pytest.raises(ValueError, match="Path traversal"):
            file_service.save_file(1, "test.txt", b"evil", subfolder="../../../../../etc")


class TestDeleteFile:
    def test_deletes_existing_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.services.file_service.STORAGE_PATH", tmp_path)
        target = tmp_path / "1" / "original"
        target.mkdir(parents=True)
        f = target / "test.txt"
        f.write_bytes(b"content")

        file_service.delete_file("1/original/test.txt")
        assert not f.exists()

    def test_silent_on_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.services.file_service.STORAGE_PATH", tmp_path)
        # Should not raise
        file_service.delete_file("nonexistent/file.txt")


class TestGetFilePath:
    def test_returns_resolved_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.services.file_service.STORAGE_PATH", tmp_path)
        target = tmp_path / "1" / "original"
        target.mkdir(parents=True)
        f = target / "doc.pdf"
        f.write_bytes(b"data")

        result = file_service.get_file_path("1/original/doc.pdf")
        assert result == f.resolve()

    def test_path_traversal_blocked(self, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.services.file_service.STORAGE_PATH", tmp_path)
        with pytest.raises(ValueError, match="Path traversal"):
            file_service.get_file_path("../../etc/passwd")
