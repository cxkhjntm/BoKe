"""Tests for /api/v1/documents endpoints."""

import pytest
import io


class TestUploadDocument:
    def test_upload_pdf(self, client, auth_headers, sample_pdf):
        content = sample_pdf.read_bytes()
        response = client.post(
            "/api/v1/documents",
            headers=auth_headers,
            files={"file": ("test.pdf", content, "application/pdf")},
            data={"title": "Test PDF"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["title"] == "Test PDF"
        assert data["file_type"] == "pdf"
        assert data["status"] in ("queued", "ready")  # sync fallback may make it ready

    def test_upload_unauthorized(self, client, sample_pdf):
        content = sample_pdf.read_bytes()
        response = client.post(
            "/api/v1/documents",
            files={"file": ("test.pdf", content, "application/pdf")},
        )
        assert response.status_code == 401

    def test_upload_disallowed_extension(self, client, auth_headers):
        response = client.post(
            "/api/v1/documents",
            headers=auth_headers,
            files={"file": ("test.exe", b"MZ", "application/octet-stream")},
        )
        assert response.status_code == 400


class TestListDocuments:
    def test_list_empty(self, client, auth_headers):
        response = client.get("/api/v1/documents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_with_documents(self, client, auth_headers, sample_pdf):
        # Upload a document first
        content = sample_pdf.read_bytes()
        client.post(
            "/api/v1/documents",
            headers=auth_headers,
            files={"file": ("test.pdf", content, "application/pdf")},
        )

        response = client.get("/api/v1/documents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_list_unauthorized(self, client):
        response = client.get("/api/v1/documents")
        assert response.status_code == 401


class TestGetDocument:
    def test_get_document(self, client, auth_headers, sample_pdf):
        content = sample_pdf.read_bytes()
        upload_resp = client.post(
            "/api/v1/documents",
            headers=auth_headers,
            files={"file": ("test.pdf", content, "application/pdf")},
        )
        doc_id = upload_resp.json()["data"]["id"]

        response = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"]["id"] == doc_id

    def test_get_nonexistent(self, client, auth_headers):
        response = client.get("/api/v1/documents/99999", headers=auth_headers)
        assert response.status_code == 404


class TestDeleteDocument:
    def test_delete_document(self, client, auth_headers, sample_pdf, db_session):
        content = sample_pdf.read_bytes()
        upload_resp = client.post(
            "/api/v1/documents",
            headers=auth_headers,
            files={"file": ("test.pdf", content, "application/pdf")},
        )
        doc_id = upload_resp.json()["data"]["id"]

        # Set status to ready (Celery task doesn't run in test env)
        from backend.models.document import Document
        doc = db_session.query(Document).filter(Document.id == doc_id).first()
        doc.status = "ready"
        db_session.commit()

        response = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
        assert response.status_code == 200

        # Verify deleted
        get_resp = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_delete_queued_document_blocked(self, client, auth_headers, sample_pdf):
        content = sample_pdf.read_bytes()
        upload_resp = client.post(
            "/api/v1/documents",
            headers=auth_headers,
            files={"file": ("test.pdf", content, "application/pdf")},
        )
        doc_id = upload_resp.json()["data"]["id"]

        # Document is in queued status — delete should be blocked
        response = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
        assert response.status_code == 409


class TestRetryDocument:
    def test_retry_failed_document(self, client, auth_headers, sample_pdf, db_session):
        content = sample_pdf.read_bytes()
        upload_resp = client.post(
            "/api/v1/documents",
            headers=auth_headers,
            files={"file": ("test.pdf", content, "application/pdf")},
        )
        doc_id = upload_resp.json()["data"]["id"]

        # Set status to error (Celery task doesn't run in test env)
        from backend.models.document import Document
        doc = db_session.query(Document).filter(Document.id == doc_id).first()
        doc.status = "error"
        db_session.commit()

        response = client.post(f"/api/v1/documents/{doc_id}/retry", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "queued"
