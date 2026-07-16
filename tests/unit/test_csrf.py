"""Unit tests for CSRF helpers."""

from __future__ import annotations

from app.web.csrf import generate_csrf_token, validate_csrf_token


def test_csrf_token_roundtrip() -> None:
    token = generate_csrf_token()
    assert validate_csrf_token(token, token)


def test_csrf_token_rejects_mismatch() -> None:
    token = generate_csrf_token()
    assert not validate_csrf_token(token, "wrong-token")


def test_csrf_token_rejects_empty() -> None:
    assert not validate_csrf_token(None, "x")
    assert not validate_csrf_token("x", None)
