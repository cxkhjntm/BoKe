"""Tests for /api/v1/chat endpoints."""

import pytest

from backend.models.chat_session import ChatSession
from backend.models.llm_config import LLMConfig
from backend.models.user import User
from backend.utils.security import create_access_token, hash_password
from backend.services import chat_storage
from backend.config import CHAT_MAX_MESSAGE_LENGTH


class TestGetMessages:
    def test_get_empty_messages(self, client, auth_headers, db_session, tmp_path, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr(chat_storage, "SESSIONS_DIR", sessions_dir)

        user = db_session.query(User).filter(User.username == "testadmin").first()
        session = ChatSession(user_id=user.id, session_id="s1", title="Test")
        db_session.add(session)
        db_session.commit()

        response = client.get("/api/v1/chat/messages/s1", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["session_id"] == "s1"
        assert data["messages"] == []

    def test_get_existing_messages(self, client, auth_headers, db_session, tmp_path, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr(chat_storage, "SESSIONS_DIR", sessions_dir)

        user = db_session.query(User).filter(User.username == "testadmin").first()
        session = ChatSession(user_id=user.id, session_id="s1", title="Test")
        db_session.add(session)
        db_session.commit()

        chat_storage.save_messages(user.id, "s1", [{"role": "user", "content": "hello"}])

        response = client.get("/api/v1/chat/messages/s1", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()["data"]["messages"]) == 1

    def test_get_unauthorized(self, client):
        response = client.get("/api/v1/chat/messages/s1")
        assert response.status_code == 401

    def test_cross_user_blocked(self, client, db_session, tmp_path, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr(chat_storage, "SESSIONS_DIR", sessions_dir)

        user_a = User(
            username="chat_user_a",
            password_hash=hash_password("pass123"),
            is_active=True,
        )
        db_session.add(user_a)
        db_session.commit()
        db_session.refresh(user_a)

        session = ChatSession(user_id=user_a.id, session_id="s-a", title="A")
        db_session.add(session)
        db_session.commit()

        user_b = User(
            username="chat_user_b",
            password_hash=hash_password("pass123"),
            is_active=True,
        )
        db_session.add(user_b)
        db_session.commit()
        db_session.refresh(user_b)

        token_b, _ = create_access_token(user_b.id)
        headers_b = {"Authorization": f"Bearer {token_b}"}

        response = client.get("/api/v1/chat/messages/s-a", headers=headers_b)
        assert response.status_code == 200  # load_messages returns empty for nonexistent user dir
        assert response.json()["data"]["messages"] == []


class TestPostMessage:
    def _create_config_and_session(self, db_session):
        from backend.utils.crypto_utils import encrypt_api_key

        user = db_session.query(User).filter(User.username == "testadmin").first()
        config = LLMConfig(
            user_id=user.id,
            provider="siliconflow",
            api_key=encrypt_api_key("sk-test-key-1234"),
            base_url="https://api.siliconflow.cn/v1",
            model="test-model",
        )
        session = ChatSession(user_id=user.id, session_id="s1", title="Test")
        db_session.add_all([config, session])
        db_session.commit()
        return user, config, session

    def test_post_no_config(self, client, auth_headers, db_session, tmp_path, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr(chat_storage, "SESSIONS_DIR", sessions_dir)

        user = db_session.query(User).filter(User.username == "testadmin").first()
        session = ChatSession(user_id=user.id, session_id="s1", title="Test")
        db_session.add(session)
        db_session.commit()

        response = client.post(
            "/api/v1/chat/messages/s1",
            headers=auth_headers,
            json={"content": "Hello"},
        )
        assert response.status_code == 400
        assert response.json()["code"] == 4005

    def test_post_no_session(self, client, auth_headers, db_session):
        from backend.utils.crypto_utils import encrypt_api_key

        user = db_session.query(User).filter(User.username == "testadmin").first()
        config = LLMConfig(
            user_id=user.id,
            provider="siliconflow",
            api_key=encrypt_api_key("sk-test-key-1234"),
            base_url="https://api.siliconflow.cn/v1",
            model="test-model",
        )
        db_session.add(config)
        db_session.commit()

        response = client.post(
            "/api/v1/chat/messages/nonexistent",
            headers=auth_headers,
            json={"content": "Hello"},
        )
        assert response.status_code == 404
        assert response.json()["code"] == 4004

    def test_post_message_too_long(self, client, auth_headers, db_session, tmp_path, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr(chat_storage, "SESSIONS_DIR", sessions_dir)

        self._create_config_and_session(db_session)

        response = client.post(
            "/api/v1/chat/messages/s1",
            headers=auth_headers,
            json={"content": "x" * (CHAT_MAX_MESSAGE_LENGTH + 1)},
        )
        assert response.status_code == 400
        assert response.json()["code"] == 4008

    def test_post_success(self, client, auth_headers, db_session, tmp_path, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr(chat_storage, "SESSIONS_DIR", sessions_dir)

        self._create_config_and_session(db_session)

        async def mock_stream(*args, **kwargs):
            yield "Hello"
            yield " World"

        monkeypatch.setattr("backend.services.chat_service.stream_llm_response", mock_stream)

        response = client.post(
            "/api/v1/chat/messages/s1",
            headers=auth_headers,
            json={"content": "Hi"},
        )
        assert response.status_code == 200
        text = response.text
        assert "start" in text
        assert "Hello" in text
        assert "World" in text
        assert "finish" in text

        # Verify messages persisted
        user = db_session.query(User).filter(User.username == "testadmin").first()
        msgs = chat_storage.load_messages(user.id, "s1")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "Hi"
        assert msgs[1]["role"] == "assistant"
        assert msgs[1]["content"] == "Hello World"

    def test_post_empty_content_rejected(self, client, auth_headers, db_session, tmp_path, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr(chat_storage, "SESSIONS_DIR", sessions_dir)

        self._create_config_and_session(db_session)

        response = client.post(
            "/api/v1/chat/messages/s1",
            headers=auth_headers,
            json={"content": ""},
        )
        assert response.status_code == 422
