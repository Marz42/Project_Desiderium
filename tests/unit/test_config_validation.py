"""Runtime configuration fail-fast tests."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.services.config_validation import validate_runtime_config


def test_repository_runtime_config_is_valid() -> None:
    validate_runtime_config(Settings(_env_file=None))


def test_production_rejects_default_secret_and_disabled_auth() -> None:
    settings = Settings(
        _env_file=None,
        ENVIRONMENT="production",
        SECRET_KEY="change-me-in-production",
        MANAGER_PASSWORD="",
    )
    with pytest.raises(ValueError, match="SECRET_KEY"):
        validate_runtime_config(settings)


def test_production_accepts_strong_auth_configuration() -> None:
    settings = Settings(
        _env_file=None,
        ENVIRONMENT="production",
        SECRET_KEY="x" * 32,
        MANAGER_PASSWORD="manager-password",
    )
    validate_runtime_config(settings)
