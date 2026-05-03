"""Tests for /api/v1/profile endpoints."""

import io

import pytest
from PIL import Image


def _make_test_image(width=100, height=100, color="blue", fmt="PNG"):
    """Create a minimal test image in memory."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf.getvalue()


class TestGetProfile:
    def test_default_profile(self, client, auth_headers):
        response = client.get("/api/v1/profile", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["avatar_path"] is None
        assert data["background_path"] is None
        assert data["background_opacity"] == 0.3

    def test_unauthenticated(self, client):
        response = client.get("/api/v1/profile")
        assert response.status_code == 401


class TestUpdateOpacity:
    def test_valid_update(self, client, auth_headers):
        response = client.put(
            "/api/v1/profile",
            json={"background_opacity": 0.7},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["data"]["background_opacity"] == 0.7

    def test_out_of_range_high(self, client, auth_headers):
        response = client.put(
            "/api/v1/profile",
            json={"background_opacity": 1.5},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_out_of_range_low(self, client, auth_headers):
        response = client.put(
            "/api/v1/profile",
            json={"background_opacity": -0.1},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestUploadAvatar:
    def test_success(self, client, auth_headers):
        image_data = _make_test_image()
        response = client.post(
            "/api/v1/profile/avatar",
            headers=auth_headers,
            files={"file": ("avatar.png", image_data, "image/png")},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["avatar_path"] is not None
        assert data["avatar_path"].endswith(".png")

    def test_replace_deletes_old(self, client, auth_headers):
        image1 = _make_test_image(color="red")
        image2 = _make_test_image(color="green")

        resp1 = client.post(
            "/api/v1/profile/avatar",
            headers=auth_headers,
            files={"file": ("avatar1.png", image1, "image/png")},
        )
        old_path = resp1.json()["data"]["avatar_path"]

        resp2 = client.post(
            "/api/v1/profile/avatar",
            headers=auth_headers,
            files={"file": ("avatar2.png", image2, "image/png")},
        )
        new_path = resp2.json()["data"]["avatar_path"]
        assert new_path != old_path

    def test_invalid_extension(self, client, auth_headers):
        response = client.post(
            "/api/v1/profile/avatar",
            headers=auth_headers,
            files={"file": ("avatar.txt", b"not an image", "text/plain")},
        )
        assert response.status_code == 400


class TestDeleteAvatar:
    def test_success(self, client, auth_headers):
        image_data = _make_test_image()
        client.post(
            "/api/v1/profile/avatar",
            headers=auth_headers,
            files={"file": ("avatar.png", image_data, "image/png")},
        )

        response = client.delete("/api/v1/profile/avatar", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"]["avatar_path"] is None

    def test_idempotent(self, client, auth_headers):
        response = client.delete("/api/v1/profile/avatar", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"]["avatar_path"] is None


class TestUploadBackground:
    def test_success(self, client, auth_headers):
        image_data = _make_test_image()
        response = client.post(
            "/api/v1/profile/background",
            headers=auth_headers,
            files={"file": ("bg.png", image_data, "image/png")},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["background_path"] is not None


class TestDeleteBackground:
    def test_success(self, client, auth_headers):
        image_data = _make_test_image()
        client.post(
            "/api/v1/profile/background",
            headers=auth_headers,
            files={"file": ("bg.png", image_data, "image/png")},
        )

        response = client.delete("/api/v1/profile/background", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"]["background_path"] is None


class TestServeProfileFiles:
    def test_avatar_with_header_auth(self, client, auth_headers):
        image_data = _make_test_image()
        client.post(
            "/api/v1/profile/avatar",
            headers=auth_headers,
            files={"file": ("avatar.png", image_data, "image/png")},
        )

        response = client.get("/api/v1/files/profile/avatar", headers=auth_headers)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/")

    def test_avatar_not_found(self, client, auth_headers):
        response = client.get("/api/v1/files/profile/avatar", headers=auth_headers)
        assert response.status_code == 404

    def test_background_with_header_auth(self, client, auth_headers):
        image_data = _make_test_image()
        client.post(
            "/api/v1/profile/background",
            headers=auth_headers,
            files={"file": ("bg.png", image_data, "image/png")},
        )

        response = client.get("/api/v1/files/profile/background", headers=auth_headers)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/")
