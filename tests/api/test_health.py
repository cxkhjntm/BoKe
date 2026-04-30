"""Tests for /api/v1/health endpoint."""

import pytest


class TestHealthCheck:
    def test_returns_health_status(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["status"] == "healthy"
        assert data["data"]["db"] == "ok"
        assert data["data"]["storage"] == "ok"
        # redis may be unavailable in test env, that's fine
        assert "redis" in data["data"]
