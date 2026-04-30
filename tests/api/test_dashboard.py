"""Tests for /api/v1/dashboard endpoints."""

import pytest


class TestDashboardStats:
    def test_stats_empty(self, client, auth_headers):
        response = client.get("/api/v1/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total_docs"] == 0
        assert data["total_size"] == 0

    def test_stats_with_documents(self, client, auth_headers, sample_pdf):
        content = sample_pdf.read_bytes()
        client.post(
            "/api/v1/documents",
            headers=auth_headers,
            files={"file": ("test.pdf", content, "application/pdf")},
        )

        response = client.get("/api/v1/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total_docs"] >= 1
        assert data["total_size"] > 0

    def test_stats_unauthorized(self, client):
        response = client.get("/api/v1/dashboard/stats")
        assert response.status_code == 401


class TestDashboardRecent:
    def test_recent_empty(self, client, auth_headers):
        response = client.get("/api/v1/dashboard/recent", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_recent_after_view(self, client, auth_headers, sample_pdf):
        content = sample_pdf.read_bytes()
        upload_resp = client.post(
            "/api/v1/documents",
            headers=auth_headers,
            files={"file": ("test.pdf", content, "application/pdf")},
        )
        doc_id = upload_resp.json()["data"]["id"]

        # View the document to trigger record_view
        client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)

        response = client.get("/api/v1/dashboard/recent", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) >= 1
        assert data[0]["id"] == doc_id


class TestDashboardTop:
    def test_top_empty(self, client, auth_headers):
        response = client.get("/api/v1/dashboard/top", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_top_after_views(self, client, auth_headers, sample_pdf, db_session):
        content = sample_pdf.read_bytes()
        upload_resp = client.post(
            "/api/v1/documents",
            headers=auth_headers,
            files={"file": ("test.pdf", content, "application/pdf")},
        )
        doc_id = upload_resp.json()["data"]["id"]

        # View the document multiple times
        for _ in range(3):
            client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)

        response = client.get("/api/v1/dashboard/top", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) >= 1
        assert data[0]["view_count"] >= 3


class TestDashboardActivity:
    def test_activity_after_upload(self, client, auth_headers, sample_pdf):
        content = sample_pdf.read_bytes()
        client.post(
            "/api/v1/documents",
            headers=auth_headers,
            files={"file": ("test.pdf", content, "application/pdf")},
        )

        response = client.get("/api/v1/dashboard/activity", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) >= 1
        actions = [a["action"] for a in data]
        assert "upload" in actions

    def test_activity_after_view(self, client, auth_headers, sample_pdf):
        content = sample_pdf.read_bytes()
        upload_resp = client.post(
            "/api/v1/documents",
            headers=auth_headers,
            files={"file": ("test.pdf", content, "application/pdf")},
        )
        doc_id = upload_resp.json()["data"]["id"]

        client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)

        response = client.get("/api/v1/dashboard/activity", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        actions = [a["action"] for a in data]
        assert "view" in actions


class TestViewCountIncrements:
    def test_view_count_increments_on_get(self, client, auth_headers, sample_pdf, db_session):
        content = sample_pdf.read_bytes()
        upload_resp = client.post(
            "/api/v1/documents",
            headers=auth_headers,
            files={"file": ("test.pdf", content, "application/pdf")},
        )
        doc_id = upload_resp.json()["data"]["id"]

        # View 3 times
        for _ in range(3):
            client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)

        # Check view_count via dashboard top
        response = client.get("/api/v1/dashboard/top", headers=auth_headers)
        data = response.json()["data"]
        doc_data = next(d for d in data if d["id"] == doc_id)
        assert doc_data["view_count"] == 3
