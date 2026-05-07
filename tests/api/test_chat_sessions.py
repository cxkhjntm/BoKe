"""Tests for /api/v1/chat-sessions endpoints."""

import pytest

from backend.models.chat_session import ChatSession
from backend.models.user import User
from backend.utils.security import create_access_token, hash_password
from backend.services import chat_storage


class TestListSessions:
    def test_empty_list(self, client, auth_headers):
        response = client.get("/api/v1/chat-sessions", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"]["items"] == []

    def test_list_with_sessions(self, client, auth_headers, db_session):
        user = db_session.query(User).filter(User.username == "testadmin").first()
        s1 = ChatSession(user_id=user.id, session_id="s1", title="Session 1")
        s2 = ChatSession(user_id=user.id, session_id="s2", title="Session 2")
        db_session.add_all([s1, s2])
        db_session.commit()

        response = client.get("/api/v1/chat-sessions", headers=auth_headers)
        assert response.status_code == 200
        items = response.json()["data"]["items"]
        assert len(items) == 2
        assert items[0]["title"] == "Session 2"  # ordered by updated_at desc

    def test_unauthorized(self, client):
        response = client.get("/api/v1/chat-sessions")
        assert response.status_code == 401


class TestCreateSession:
    def test_create_success(self, client, auth_headers):
        response = client.post(
            "/api/v1/chat-sessions",
            headers=auth_headers,
            json={"title": "My Chat"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["title"] == "My Chat"
        assert "session_id" in data

    def test_default_title(self, client, auth_headers):
        response = client.post(
            "/api/v1/chat-sessions",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 200
        assert response.json()["data"]["title"] == "新会话"


class TestUpdateSession:
    def test_update_success(self, client, auth_headers, db_session):
        user = db_session.query(User).filter(User.username == "testadmin").first()
        session = ChatSession(user_id=user.id, session_id="s1", title="Old")
        db_session.add(session)
        db_session.commit()

        response = client.patch(
            "/api/v1/chat-sessions/s1",
            headers=auth_headers,
            json={"title": "New"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["title"] == "New"

    def test_update_not_found(self, client, auth_headers):
        response = client.patch(
            "/api/v1/chat-sessions/nonexistent",
            headers=auth_headers,
            json={"title": "New"},
        )
        assert response.status_code == 404


class TestDeleteSession:
    def test_delete_success(self, client, auth_headers, db_session, tmp_path, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr(chat_storage, "SESSIONS_DIR", sessions_dir)

        user = db_session.query(User).filter(User.username == "testadmin").first()
        session = ChatSession(user_id=user.id, session_id="s1", title="To Delete")
        db_session.add(session)
        db_session.commit()

        # Add some messages
        chat_storage.save_messages(user.id, "s1", [{"role": "user", "content": "hi"}])

        response = client.delete("/api/v1/chat-sessions/s1", headers=auth_headers)
        assert response.status_code == 200

        # Verify DB record gone
        assert (
            db_session.query(ChatSession).filter(ChatSession.session_id == "s1").first()
            is None
        )
        # Verify files cleaned
        assert not (sessions_dir / str(user.id) / "s1.json").exists()

    def test_delete_not_found(self, client, auth_headers):
        response = client.delete("/api/v1/chat-sessions/nonexistent", headers=auth_headers)
        assert response.status_code == 404


class TestCrossUserAccess:
    def test_user_cannot_see_others_sessions(self, client, db_session):
        user_a = User(
            username="session_user_a",
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
            username="session_user_b",
            password_hash=hash_password("pass123"),
            is_active=True,
        )
        db_session.add(user_b)
        db_session.commit()
        db_session.refresh(user_b)

        token_b, _ = create_access_token(user_b.id)
        headers_b = {"Authorization": f"Bearer {token_b}"}

        response = client.get("/api/v1/chat-sessions", headers=headers_b)
        assert response.json()["data"]["items"] == []

    def test_user_cannot_delete_others_session(self, client, db_session):
        user_a = User(
            username="session_user_a2",
            password_hash=hash_password("pass123"),
            is_active=True,
        )
        db_session.add(user_a)
        db_session.commit()
        db_session.refresh(user_a)

        session = ChatSession(user_id=user_a.id, session_id="s-a2", title="A")
        db_session.add(session)
        db_session.commit()

        user_b = User(
            username="session_user_b2",
            password_hash=hash_password("pass123"),
            is_active=True,
        )
        db_session.add(user_b)
        db_session.commit()
        db_session.refresh(user_b)

        token_b, _ = create_access_token(user_b.id)
        headers_b = {"Authorization": f"Bearer {token_b}"}

        response = client.delete("/api/v1/chat-sessions/s-a2", headers=headers_b)
        assert response.status_code == 404

    def test_user_cannot_update_others_session(self, client, db_session):
        user_a = User(
            username="session_user_a3",
            password_hash=hash_password("pass123"),
            is_active=True,
        )
        db_session.add(user_a)
        db_session.commit()
        db_session.refresh(user_a)

        session = ChatSession(user_id=user_a.id, session_id="s-a3", title="A")
        db_session.add(session)
        db_session.commit()

        user_b = User(
            username="session_user_b3",
            password_hash=hash_password("pass123"),
            is_active=True,
        )
        db_session.add(user_b)
        db_session.commit()
        db_session.refresh(user_b)

        token_b, _ = create_access_token(user_b.id)
        headers_b = {"Authorization": f"Bearer {token_b}"}

        response = client.patch(
            "/api/v1/chat-sessions/s-a3",
            headers=headers_b,
            json={"title": "Hacked"},
        )
        assert response.status_code == 404
