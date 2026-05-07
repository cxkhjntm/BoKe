"""Tests for /api/v1/llm-config endpoints."""

import pytest

from backend.models.llm_config import LLMConfig
from backend.utils.security import create_access_token, hash_password
from backend.models.user import User


class TestGetLLMConfig:
    def test_empty_when_not_set(self, client, auth_headers):
        response = client.get("/api/v1/llm-config", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"] is None

    def test_returns_masked_key(self, client, auth_headers, db_session):
        from backend.utils.crypto_utils import encrypt_api_key

        user = db_session.query(User).filter(User.username == "testadmin").first()
        config = LLMConfig(
            user_id=user.id,
            provider="siliconflow",
            api_key=encrypt_api_key("sk-test-secret-key-1234"),
            base_url="https://api.siliconflow.cn/v1",
            model="Qwen/Qwen2.5-7B-Instruct",
        )
        db_session.add(config)
        db_session.commit()

        response = client.get("/api/v1/llm-config", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["provider"] == "siliconflow"
        assert "***" in data["api_key"]
        # Masking is applied to the encrypted key, not plaintext
        assert len(data["api_key"]) > 12
        assert data["base_url"] == "https://api.siliconflow.cn/v1"
        assert data["model"] == "Qwen/Qwen2.5-7B-Instruct"


class TestUpsertLLMConfig:
    def test_create_config(self, client, auth_headers):
        response = client.post(
            "/api/v1/llm-config",
            headers=auth_headers,
            json={
                "provider": "siliconflow",
                "api_key": "sk-test-secret-key-1234",
                "base_url": "https://api.siliconflow.cn/v1",
                "model": "Qwen/Qwen2.5-7B-Instruct",
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["provider"] == "siliconflow"
        assert data["model"] == "Qwen/Qwen2.5-7B-Instruct"

    def test_update_existing(self, client, auth_headers):
        client.post(
            "/api/v1/llm-config",
            headers=auth_headers,
            json={
                "provider": "siliconflow",
                "api_key": "sk-old-key-1234",
                "base_url": "https://api.siliconflow.cn/v1",
                "model": "old-model",
            },
        )
        response = client.post(
            "/api/v1/llm-config",
            headers=auth_headers,
            json={
                "provider": "deepseek",
                "api_key": "sk-new-key-5678",
                "base_url": "https://api.deepseek.com/v1",
                "model": "deepseek-chat",
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["provider"] == "deepseek"
        assert data["model"] == "deepseek-chat"

    def test_invalid_base_url_blocked(self, client, auth_headers):
        response = client.post(
            "/api/v1/llm-config",
            headers=auth_headers,
            json={
                "provider": "evil",
                "api_key": "sk-test-secret-key-1234",
                "base_url": "https://evil.com/api",
                "model": "evil-model",
            },
        )
        assert response.status_code == 422

    def test_short_api_key_rejected(self, client, auth_headers):
        response = client.post(
            "/api/v1/llm-config",
            headers=auth_headers,
            json={
                "provider": "siliconflow",
                "api_key": "short",
                "base_url": "https://api.siliconflow.cn/v1",
                "model": "model",
            },
        )
        assert response.status_code == 422

    def test_empty_model_rejected(self, client, auth_headers):
        response = client.post(
            "/api/v1/llm-config",
            headers=auth_headers,
            json={
                "provider": "siliconflow",
                "api_key": "sk-test-secret-key-1234",
                "base_url": "https://api.siliconflow.cn/v1",
                "model": "",
            },
        )
        assert response.status_code == 422


class TestDeleteLLMConfig:
    def test_delete_existing(self, client, auth_headers):
        client.post(
            "/api/v1/llm-config",
            headers=auth_headers,
            json={
                "provider": "siliconflow",
                "api_key": "sk-test-secret-key-1234",
                "base_url": "https://api.siliconflow.cn/v1",
                "model": "model",
            },
        )
        response = client.delete("/api/v1/llm-config", headers=auth_headers)
        assert response.status_code == 200

        get_resp = client.get("/api/v1/llm-config", headers=auth_headers)
        assert get_resp.json()["data"] is None

    def test_idempotent_delete(self, client, auth_headers):
        response = client.delete("/api/v1/llm-config", headers=auth_headers)
        assert response.status_code == 200


class TestCrossUserAccess:
    def test_user_cannot_see_others_config(self, client, db_session):
        # Create user A with config
        user_a = User(
            username="user_a",
            password_hash=hash_password("pass123"),
            is_active=True,
        )
        db_session.add(user_a)
        db_session.commit()
        db_session.refresh(user_a)

        from backend.utils.crypto_utils import encrypt_api_key

        config = LLMConfig(
            user_id=user_a.id,
            provider="siliconflow",
            api_key=encrypt_api_key("sk-a"),
            base_url="https://api.siliconflow.cn/v1",
            model="model-a",
        )
        db_session.add(config)
        db_session.commit()

        # Create user B
        user_b = User(
            username="user_b",
            password_hash=hash_password("pass123"),
            is_active=True,
        )
        db_session.add(user_b)
        db_session.commit()
        db_session.refresh(user_b)

        token_b, _ = create_access_token(user_b.id)
        headers_b = {"Authorization": f"Bearer {token_b}"}

        response = client.get("/api/v1/llm-config", headers=headers_b)
        assert response.status_code == 200
        assert response.json()["data"] is None

    def test_user_cannot_update_others_config(self, client, db_session):
        # Create user A with config
        user_a = User(
            username="user_a2",
            password_hash=hash_password("pass123"),
            is_active=True,
        )
        db_session.add(user_a)
        db_session.commit()
        db_session.refresh(user_a)

        from backend.utils.crypto_utils import encrypt_api_key

        config = LLMConfig(
            user_id=user_a.id,
            provider="siliconflow",
            api_key=encrypt_api_key("sk-a"),
            base_url="https://api.siliconflow.cn/v1",
            model="model-a",
        )
        db_session.add(config)
        db_session.commit()

        # User B upserts — should create their own config, not modify A's
        user_b = User(
            username="user_b2",
            password_hash=hash_password("pass123"),
            is_active=True,
        )
        db_session.add(user_b)
        db_session.commit()
        db_session.refresh(user_b)

        token_b, _ = create_access_token(user_b.id)
        headers_b = {"Authorization": f"Bearer {token_b}"}

        response = client.post(
            "/api/v1/llm-config",
            headers=headers_b,
            json={
                "provider": "deepseek",
                "api_key": "sk-test-secret-key-1234",
                "base_url": "https://api.deepseek.com/v1",
                "model": "model-b",
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["provider"] == "deepseek"

        # Verify user A's config is unchanged
        db_session.refresh(config)
        assert config.provider == "siliconflow"
