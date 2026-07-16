"""Signed cookie session helpers (stdlib only)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any

from starlette.requests import Request

from app.config import get_settings

SESSION_COOKIE = "desiderium_session"


def sign_session(data: dict[str, Any], secret: str) -> str:
    payload = base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode()).decode()
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def verify_session(token: str, secret: str) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    payload, sig = token.rsplit(".", 1)
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        raw = base64.urlsafe_b64decode(payload.encode())
        data = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def get_session_data(request: Request) -> dict[str, Any]:
    settings = get_settings()
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return {}
    return verify_session(token, settings.secret_key) or {}


def get_csrf_token(request: Request) -> str:
    session = get_session_data(request)
    return str(session.get("csrf_token") or "")
