"""Authentication utilities — password hashing, token management."""

from __future__ import annotations

import hashlib
import secrets
import time
from typing import Any

from fastapi import Request


_AUTH_SECRET = secrets.token_hex(32)
_TOKEN_EXPIRY = 86400 * 7  # 7 days

# Active tokens: token -> {user_id, email, role, display_name, expires}
_active_tokens: dict[str, dict[str, Any]] = {}


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain password against its hash."""
    return hash_password(plain_password) == hashed_password


def create_token(user_id: int, email: str, role: str, display_name: str) -> str:
    """Create a signed auth token and store it in memory."""
    token = secrets.token_urlsafe(48)
    _active_tokens[token] = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "display_name": display_name,
        "expires": time.time() + _TOKEN_EXPIRY,
    }
    return token


def verify_token(token: str) -> dict[str, Any] | None:
    """Verify and return token data, or None if invalid/expired."""
    data = _active_tokens.get(token)
    if not data:
        return None
    if time.time() > data["expires"]:
        _active_tokens.pop(token, None)
        return None
    return data


def revoke_token(token: str) -> None:
    """Remove a token from active tokens."""
    _active_tokens.pop(token, None)


def get_token_from_request(request: Request) -> str | None:
    """Extract token from Authorization header or cookie."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("auth_token")


TOKEN_EXPIRY = _TOKEN_EXPIRY
