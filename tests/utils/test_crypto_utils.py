"""Tests for backend.utils.crypto_utils."""

import base64

import pytest

from backend.utils.crypto_utils import encrypt_api_key, decrypt_api_key


class TestEncryptDecrypt:
    def test_roundtrip(self):
        plain = "sk-test-api-key-12345"
        cipher = encrypt_api_key(plain)
        assert cipher != plain
        decrypted = decrypt_api_key(cipher)
        assert decrypted == plain

    def test_different_nonce_each_time(self):
        plain = "same-key"
        cipher1 = encrypt_api_key(plain)
        cipher2 = encrypt_api_key(plain)
        assert cipher1 != cipher2

    def test_decrypt_invalid_base64(self):
        with pytest.raises(Exception):
            decrypt_api_key("not-valid-base64!!!")

    def test_decrypt_tampered_ciphertext(self):
        plain = "sk-test"
        cipher = encrypt_api_key(plain)
        raw = bytearray(base64.b64decode(cipher.encode()))
        # Tamper with the ciphertext portion (after nonce)
        raw[-1] ^= 0xFF
        tampered = base64.b64encode(bytes(raw)).decode()
        with pytest.raises(Exception):
            decrypt_api_key(tampered)

    def test_decrypt_truncated_data(self):
        with pytest.raises(Exception):
            decrypt_api_key(base64.b64encode(b"short").decode())

    def test_unicode_roundtrip(self):
        plain = "密钥-🗝️-test"
        cipher = encrypt_api_key(plain)
        assert decrypt_api_key(cipher) == plain
