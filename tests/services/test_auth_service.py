"""Tests for backend.services.auth_service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from backend.services import auth_service
from backend.models.user import User
from backend.models.refresh_token import RefreshToken
from backend.utils.security import hash_password, create_access_token, create_refresh_token
from backend.exceptions.handlers import AppException


class TestAuthenticate:
    def _make_user(self, db_session, username="testuser", password="pass123", is_admin=False):
        user = User(
            username=username,
            password_hash=hash_password(password),
            is_admin=is_admin,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    def test_valid_credentials(self, db_session):
        self._make_user(db_session)
        result = auth_service.authenticate(db_session, "testuser", "pass123")

        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"

    def test_invalid_username(self, db_session):
        self._make_user(db_session)
        with pytest.raises(AppException) as exc_info:
            auth_service.authenticate(db_session, "wrong", "pass123")
        assert exc_info.value.status_code == 401

    def test_invalid_password(self, db_session):
        self._make_user(db_session)
        with pytest.raises(AppException) as exc_info:
            auth_service.authenticate(db_session, "testuser", "wrong")
        assert exc_info.value.status_code == 401

    def test_account_lockout(self, db_session):
        user = self._make_user(db_session)
        user.login_failures = 10
        user.locked_until = datetime.utcnow() + timedelta(minutes=10)
        db_session.commit()

        with pytest.raises(AppException) as exc_info:
            auth_service.authenticate(db_session, "testuser", "pass123")
        assert exc_info.value.status_code == 423

    def test_failed_attempt_increments_count(self, db_session):
        self._make_user(db_session)
        with pytest.raises(AppException):
            auth_service.authenticate(db_session, "testuser", "wrong")

        user = db_session.query(User).filter(User.username == "testuser").first()
        assert user.login_failures == 1

    def test_successful_login_resets_failures(self, db_session):
        user = self._make_user(db_session)
        user.login_failures = 5
        db_session.commit()

        auth_service.authenticate(db_session, "testuser", "pass123")
        user = db_session.query(User).filter(User.username == "testuser").first()
        assert user.login_failures == 0
        assert user.locked_until is None


class TestRefresh:
    def test_valid_refresh(self, db_session):
        user = User(
            username="refreshuser",
            password_hash=hash_password("pass"),
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token, jti, expires = create_refresh_token(user.id)
        rt = RefreshToken(user_id=user.id, jti=jti, expires_at=expires)
        db_session.add(rt)
        db_session.commit()

        result = auth_service.refresh(db_session, token)
        assert "access_token" in result
        assert "refresh_token" in result
        # Old token should be revoked
        old_rt = db_session.query(RefreshToken).filter(RefreshToken.jti == jti).first()
        assert old_rt.revoked is True

    def test_invalid_token(self, db_session):
        with pytest.raises(AppException) as exc_info:
            auth_service.refresh(db_session, "invalid-token")
        assert exc_info.value.status_code == 401

    def test_revoked_token_triggers_family_revoke(self, db_session):
        user = User(
            username="familyuser",
            password_hash=hash_password("pass"),
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token, jti, expires = create_refresh_token(user.id)
        rt = RefreshToken(user_id=user.id, jti=jti, expires_at=expires, revoked=True)
        db_session.add(rt)
        db_session.commit()

        with pytest.raises(AppException):
            auth_service.refresh(db_session, token)


class TestLogout:
    def test_revokes_token(self, db_session):
        user = User(
            username="logoutuser",
            password_hash=hash_password("pass"),
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token, jti, expires = create_refresh_token(user.id)
        rt = RefreshToken(user_id=user.id, jti=jti, expires_at=expires)
        db_session.add(rt)
        db_session.commit()

        auth_service.logout(db_session, user.id, token)
        rt = db_session.query(RefreshToken).filter(RefreshToken.jti == jti).first()
        assert rt.revoked is True

    def test_invalid_token_no_error(self, db_session):
        # Should not raise even with bad token
        auth_service.logout(db_session, 999, "bad-token")
