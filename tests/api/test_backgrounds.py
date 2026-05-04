"""Tests for multi-background endpoints."""

import io
import pytest
from PIL import Image


def _make_test_image(width=100, height=100, color="blue", fmt="PNG"):
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf.getvalue()


class TestListBackgrounds:
    def test_empty_list(self, client, auth_headers):
        response = client.get("/api/v1/profile/backgrounds", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_unauthenticated(self, client):
        response = client.get("/api/v1/profile/backgrounds")
        assert response.status_code == 401


class TestUploadBackgroundMulti:
    def test_success(self, client, auth_headers):
        image_data = _make_test_image()
        response = client.post(
            "/api/v1/profile/backgrounds",
            headers=auth_headers,
            files={"file": ("bg1.png", image_data, "image/png")},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] is not None
        assert data["position"] == 0

    def test_multiple_uploads_increment_position(self, client, auth_headers):
        for i in range(3):
            image_data = _make_test_image(color=["red", "green", "blue"][i])
            resp = client.post(
                "/api/v1/profile/backgrounds",
                headers=auth_headers,
                files={"file": (f"bg{i}.png", image_data, "image/png")},
            )
            assert resp.status_code == 200
            assert resp.json()["data"]["position"] == i

    def test_max_limit(self, client, auth_headers):
        image_data = _make_test_image()
        for i in range(10):
            client.post(
                "/api/v1/profile/backgrounds",
                headers=auth_headers,
                files={"file": (f"bg{i}.png", image_data, "image/png")},
            )
        response = client.post(
            "/api/v1/profile/backgrounds",
            headers=auth_headers,
            files={"file": ("bg11.png", image_data, "image/png")},
        )
        assert response.status_code == 400


class TestDeleteBackgroundMulti:
    def test_success(self, client, auth_headers):
        image_data = _make_test_image()
        resp = client.post(
            "/api/v1/profile/backgrounds",
            headers=auth_headers,
            files={"file": ("bg.png", image_data, "image/png")},
        )
        bg_id = resp.json()["data"]["id"]

        response = client.delete(f"/api/v1/profile/backgrounds/{bg_id}", headers=auth_headers)
        assert response.status_code == 200

        list_resp = client.get("/api/v1/profile/backgrounds", headers=auth_headers)
        assert list_resp.json()["data"] == []

    def test_not_found(self, client, auth_headers):
        response = client.delete("/api/v1/profile/backgrounds/999", headers=auth_headers)
        assert response.status_code == 404

    def test_reorder_after_delete(self, client, auth_headers):
        image_data = _make_test_image()
        ids = []
        for i in range(3):
            resp = client.post(
                "/api/v1/profile/backgrounds",
                headers=auth_headers,
                files={"file": (f"bg{i}.png", image_data, "image/png")},
            )
            ids.append(resp.json()["data"]["id"])

        client.delete(f"/api/v1/profile/backgrounds/{ids[1]}", headers=auth_headers)

        list_resp = client.get("/api/v1/profile/backgrounds", headers=auth_headers)
        remaining = list_resp.json()["data"]
        assert len(remaining) == 2
        assert remaining[0]["position"] == 0
        assert remaining[1]["position"] == 1


class TestReorderBackgrounds:
    def test_success(self, client, auth_headers):
        image_data = _make_test_image()
        ids = []
        for i in range(3):
            resp = client.post(
                "/api/v1/profile/backgrounds",
                headers=auth_headers,
                files={"file": (f"bg{i}.png", image_data, "image/png")},
            )
            ids.append(resp.json()["data"]["id"])

        response = client.put(
            "/api/v1/profile/backgrounds/reorder",
            headers=auth_headers,
            json={"background_ids": list(reversed(ids))},
        )
        assert response.status_code == 200

        list_resp = client.get("/api/v1/profile/backgrounds", headers=auth_headers)
        reordered = list_resp.json()["data"]
        assert [bg["id"] for bg in reordered] == list(reversed(ids))


class TestCarouselInterval:
    def test_default_interval(self, client, auth_headers):
        response = client.get("/api/v1/profile", headers=auth_headers)
        assert response.json()["data"]["carousel_interval"] == 5

    def test_update_interval(self, client, auth_headers):
        response = client.put(
            "/api/v1/profile",
            headers=auth_headers,
            json={"carousel_interval": 10},
        )
        assert response.status_code == 200
        assert response.json()["data"]["carousel_interval"] == 10

    def test_interval_too_low(self, client, auth_headers):
        response = client.put(
            "/api/v1/profile",
            headers=auth_headers,
            json={"carousel_interval": 0},
        )
        assert response.status_code == 422

    def test_interval_too_high(self, client, auth_headers):
        response = client.put(
            "/api/v1/profile",
            headers=auth_headers,
            json={"carousel_interval": 301},
        )
        assert response.status_code == 422
