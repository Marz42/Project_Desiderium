"""CSRF token generation and validation."""

from __future__ import annotations

import secrets


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def validate_csrf_token(session_token: str | None, submitted: str | None) -> bool:
    if not session_token or not submitted:
        return False
    return secrets.compare_digest(session_token, submitted)
