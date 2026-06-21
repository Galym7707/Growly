"""Backend-only encryption for user-supplied secrets (e.g. Blotato API keys).

Secrets are stored encrypted at rest and are never returned to the frontend.
When the optional ``cryptography`` package is installed (production), Fernet
(AES-128-CBC + HMAC) is used. Otherwise the code degrades to an HMAC-SHA256
keystream cipher built from the standard library so the feature still works in
minimal/dev environments. The stored blob is prefixed with the scheme name so
decryption always knows how a value was encrypted.

The encryption key is derived from ``SECRETS_ENCRYPTION_KEY`` when configured,
falling back to ``GROWLY_WEB_API_KEY``. Both live only in backend secrets.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os

from app.config import get_settings

logger = logging.getLogger(__name__)

try:  # pragma: no cover - depends on optional dependency
    from cryptography.fernet import Fernet

    _HAS_FERNET = True
except Exception:  # pragma: no cover - cryptography is optional
    _HAS_FERNET = False

_FERNET_PREFIX = "fernet:"
_XOR_PREFIX = "xor:"
_NONCE_SIZE = 16


def _server_secret() -> bytes:
    settings = get_settings()
    explicit = settings.secrets_encryption_key
    if explicit and explicit.get_secret_value().strip():
        return explicit.get_secret_value().strip().encode("utf-8")
    web = settings.growly_web_api_key
    if web and web.get_secret_value().strip():
        return web.get_secret_value().strip().encode("utf-8")
    logger.warning(
        "No SECRETS_ENCRYPTION_KEY/GROWLY_WEB_API_KEY set; using a development "
        "fallback to encrypt stored secrets. Configure a key for production."
    )
    return b"growly-development-secret-key"


def _fernet() -> "Fernet":
    digest = hashlib.sha256(_server_secret()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _keystream(nonce: bytes, length: int) -> bytes:
    secret = _server_secret()
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hmac.new(
            secret, nonce + counter.to_bytes(4, "big"), hashlib.sha256
        ).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def encrypt_secret(value: str) -> str:
    """Encrypt a secret for storage. Returns a scheme-prefixed string."""

    data = value.encode("utf-8")
    if _HAS_FERNET:
        token = _fernet().encrypt(data).decode("ascii")
        return _FERNET_PREFIX + token
    nonce = os.urandom(_NONCE_SIZE)
    keystream = _keystream(nonce, len(data))
    cipher = bytes(b ^ k for b, k in zip(data, keystream))
    blob = base64.urlsafe_b64encode(nonce + cipher).decode("ascii")
    return _XOR_PREFIX + blob


def decrypt_secret(stored: str | None) -> str | None:
    """Decrypt a stored secret. Returns ``None`` if it cannot be recovered."""

    if not stored:
        return None
    try:
        if stored.startswith(_FERNET_PREFIX):
            if not _HAS_FERNET:
                logger.warning("Stored secret needs cryptography to decrypt.")
                return None
            token = stored[len(_FERNET_PREFIX):].encode("ascii")
            return _fernet().decrypt(token).decode("utf-8")
        if stored.startswith(_XOR_PREFIX):
            blob = base64.urlsafe_b64decode(
                stored[len(_XOR_PREFIX):].encode("ascii")
            )
            nonce, cipher = blob[:_NONCE_SIZE], blob[_NONCE_SIZE:]
            keystream = _keystream(nonce, len(cipher))
            return bytes(c ^ k for c, k in zip(cipher, keystream)).decode("utf-8")
    except Exception:  # noqa: BLE001 - never surface secret-handling internals
        logger.warning("Failed to decrypt a stored secret.")
        return None
    return None
