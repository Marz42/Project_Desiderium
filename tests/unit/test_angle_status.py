"""Unit tests for creative angle status machine."""

from __future__ import annotations

import pytest

from app.models import AngleStatus
from app.services.angle_status import AngleStatusService, InvalidStatusTransition, VALID_TRANSITIONS


def test_valid_transitions_from_candidate() -> None:
    allowed = VALID_TRANSITIONS[AngleStatus.CANDIDATE]
    assert AngleStatus.SELECTED in allowed
    assert AngleStatus.BLOCKED in allowed
    assert AngleStatus.ADOPTED not in allowed


def test_valid_transitions_from_selected() -> None:
    allowed = VALID_TRANSITIONS[AngleStatus.SELECTED]
    assert AngleStatus.ADOPTED in allowed
    assert AngleStatus.CANDIDATE in allowed
    assert AngleStatus.BLOCKED in allowed


def test_can_transition_same_status() -> None:
    svc = AngleStatusService(session=None)  # type: ignore[arg-type]
    assert svc.can_transition(AngleStatus.CANDIDATE, AngleStatus.CANDIDATE)


def test_invalid_transition_raises() -> None:
    svc = AngleStatusService(session=None)  # type: ignore[arg-type]
    assert not svc.can_transition(AngleStatus.CANDIDATE, AngleStatus.PUBLISHED)


def test_blocked_is_terminal() -> None:
    assert VALID_TRANSITIONS[AngleStatus.BLOCKED] == set()
