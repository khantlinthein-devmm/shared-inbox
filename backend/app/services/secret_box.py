"""Encrypts channel credentials at rest with a key derived from SECRET_KEY."""

import base64
import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(f"channel-secrets:{get_settings().secret_key}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def seal(values: dict) -> str:
    return _fernet().encrypt(json.dumps(values).encode()).decode()


def unseal(token: str) -> dict | None:
    """Return the stored values, or None if they can't be decrypted (SECRET_KEY changed)."""
    try:
        return json.loads(_fernet().decrypt(token.encode()))
    except (InvalidToken, ValueError):
        return None
