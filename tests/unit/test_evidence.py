"""Unit tests for evidence ID validation."""

from __future__ import annotations

import pytest

from app.services.evidence import require_evidence_ids, validate_evidence_ids


def test_validate_evidence_ids_filters_unknown() -> None:
    allowed = {"a", "b", "c"}
    assert validate_evidence_ids(["a", "x", "b"], allowed) == ["a", "b"]


def test_validate_evidence_ids_empty_when_none_match() -> None:
    assert validate_evidence_ids(["x"], {"a"}) == []


def test_require_evidence_ids_raises() -> None:
    with pytest.raises(ValueError, match="no valid evidence"):
        require_evidence_ids(["bad"], {"good"})
