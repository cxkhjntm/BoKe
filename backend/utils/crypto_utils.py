import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.config import JWT_SECRET_KEY

_SALT = b"bo-ke-llm-v1"
_ITERATIONS = 100000
_DKLEN = 32


def _derive_key() -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        JWT_SECRET_KEY.encode(),
        _SALT,
        _ITERATIONS,
        dklen=_DKLEN,
    )


def encrypt_api_key(plain: str) -> str:
    """Encrypt an API key using AES-256-GCM. Returns base64(nonce + ciphertext + tag)."""
    nonce = os.urandom(12)
    ct = AESGCM(_derive_key()).encrypt(nonce, plain.encode(), None)
    return base64.b64encode(nonce + ct).decode()


def decrypt_api_key(cipher: str) -> str:
    """Decrypt an API key encrypted with encrypt_api_key."""
    raw = base64.b64decode(cipher.encode())
    nonce, ct = raw[:12], raw[12:]
    return AESGCM(_derive_key()).decrypt(nonce, ct, None).decode()
