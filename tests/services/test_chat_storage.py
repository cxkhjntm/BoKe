"""Tests for backend.services.chat_storage."""

import json

import pytest

from backend.services import chat_storage


class TestLoadSaveMessages:
    def test_load_empty(self, tmp_path, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr(chat_storage, "SESSIONS_DIR", sessions_dir)

        msgs = chat_storage.load_messages(1, "nonexistent")
        assert msgs == []

    def test_save_and_load(self, tmp_path, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr(chat_storage, "SESSIONS_DIR", sessions_dir)

        messages = [
            {"role": "system", "content": "You are a helper."},
            {"role": "user", "content": "Hello"},
        ]
        chat_storage.save_messages(1, "s1", messages)
        loaded = chat_storage.load_messages(1, "s1")
        assert loaded == messages

    def test_overwrite_existing(self, tmp_path, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr(chat_storage, "SESSIONS_DIR", sessions_dir)

        chat_storage.save_messages(1, "s1", [{"role": "user", "content": "old"}])
        chat_storage.save_messages(1, "s1", [{"role": "user", "content": "new"}])
        loaded = chat_storage.load_messages(1, "s1")
        assert loaded[0]["content"] == "new"

    def test_file_permissions(self, tmp_path, monkeypatch):
        import os

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr(chat_storage, "SESSIONS_DIR", sessions_dir)

        chat_storage.save_messages(1, "s1", [{"role": "user", "content": "hi"}])
        path = sessions_dir / "1" / "s1.json"
        assert path.exists()
        mode = path.stat().st_mode
        assert mode & 0o777 == 0o600


class TestTrimMessages:
    def test_zero_max_rounds_returns_all(self):
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
        ]
        result = chat_storage.trim_messages(msgs, 0)
        assert result == msgs

    def test_trims_to_max_rounds(self):
        msgs = [
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "u2"},
            {"role": "assistant", "content": "a2"},
            {"role": "user", "content": "u3"},
            {"role": "assistant", "content": "a3"},
        ]
        result = chat_storage.trim_messages(msgs, 2)
        assert len(result) == 4
        assert result[0]["content"] == "u2"
        assert result[-1]["content"] == "a3"

    def test_preserves_system_messages(self):
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "u2"},
            {"role": "assistant", "content": "a2"},
            {"role": "user", "content": "u3"},
            {"role": "assistant", "content": "a3"},
        ]
        result = chat_storage.trim_messages(msgs, 1)
        assert len(result) == 3
        assert result[0]["role"] == "system"
        assert result[1]["content"] == "u3"


class TestPathTraversal:
    def test_path_traversal_blocked(self, tmp_path, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr(chat_storage, "SESSIONS_DIR", sessions_dir)

        with pytest.raises(ValueError, match="Path traversal"):
            chat_storage._session_path(1, "../../../etc/passwd")

    def test_valid_path_allowed(self, tmp_path, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr(chat_storage, "SESSIONS_DIR", sessions_dir)

        path = chat_storage._session_path(1, "abc-123")
        assert path.exists() is False
        assert path.name == "abc-123.json"


class TestDeleteSessionFiles:
    def test_deletes_json_and_lock(self, tmp_path, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr(chat_storage, "SESSIONS_DIR", sessions_dir)

        chat_storage.save_messages(1, "s1", [{"role": "user", "content": "hi"}])
        chat_storage.delete_session_files(1, "s1")

        path = sessions_dir / "1" / "s1.json"
        lock_path = sessions_dir / "1" / "s1.json.lock"
        assert not path.exists()
        assert not lock_path.exists()

    def test_idempotent_delete(self, tmp_path, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr(chat_storage, "SESSIONS_DIR", sessions_dir)

        # Should not raise when files don't exist
        chat_storage.delete_session_files(1, "missing")
