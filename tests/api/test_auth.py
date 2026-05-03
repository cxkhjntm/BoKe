"""Tests for /api/v1/auth endpoints."""

import pytest


class TestLogin:
    def test_valid_login(self, client, admin_user):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testadmin", "password": "testpass123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
        assert "user" in data["data"]
        assert data["data"]["user"]["username"] == "testadmin"
        assert data["data"]["user"]["avatar_path"] is None
        assert data["data"]["user"]["background_path"] is None
        assert data["data"]["user"]["background_opacity"] == 0.3

    def test_invalid_password(self, client, admin_user):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testadmin", "password": "wrong"},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["code"] == 4001

    def test_invalid_username(self, client, admin_user):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "nobody", "password": "testpass123"},
        )
        assert response.status_code == 401

    def test_missing_fields(self, client):
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422


class TestRefresh:
    def test_valid_refresh(self, client, admin_user):
        # Login first
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"username": "testadmin", "password": "testpass123"},
        )
        refresh_token = login_resp.json()["data"]["refresh_token"]

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    def test_invalid_refresh_token(self, client):
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid"},
        )
        assert response.status_code == 401


class TestLogout:
    def test_logout(self, client, admin_user):
        # Login first
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"username": "testadmin", "password": "testpass123"},
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.json()}"
        tokens = login_resp.json()["data"]

        response = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert response.status_code == 200
        assert response.json()["code"] == 0

    def test_logout_without_auth(self, client):
        response = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": "some-token"},
        )
        assert response.status_code == 401  # get_current_user raises 401
