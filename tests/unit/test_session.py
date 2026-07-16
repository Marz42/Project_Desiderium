"""Unit tests for signed session cookies."""

from __future__ import annotations

from app.web.session import sign_session, verify_session


def test_session_sign_and_verify() -> None:
    data = {"authenticated": True, "csrf_token": "abc"}
    token = sign_session(data, "test-secret")
    restored = verify_session(token, "test-secret")
    assert restored == data


def test_session_rejects_tampered_token() -> None:
    token = sign_session({"authenticated": True}, "test-secret")
    tampered = token[:-2] + "xx"
    assert verify_session(tampered, "test-secret") is None


def test_session_rejects_wrong_secret() -> None:
    token = sign_session({"authenticated": True}, "test-secret")
    assert verify_session(token, "other-secret") is None
