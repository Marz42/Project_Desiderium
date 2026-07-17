from __future__ import annotations

import pytest

from app.domain.membership_policy import may_reactivate_membership
from app.models import MembershipMethod


@pytest.mark.parametrize(
    "incoming",
    [
        MembershipMethod.RULE,
        MembershipMethod.EMBEDDING,
        MembershipMethod.LLM,
    ],
)
def test_manual_inactive_membership_blocks_automatic_reactivation(
    incoming: MembershipMethod,
) -> None:
    assert not may_reactivate_membership(MembershipMethod.MANUAL, False, incoming)


def test_manual_inactive_membership_allows_explicit_manual_restore() -> None:
    assert may_reactivate_membership(
        MembershipMethod.MANUAL,
        False,
        MembershipMethod.MANUAL,
    )


@pytest.mark.parametrize(
    ("existing", "incoming", "allowed"),
    [
        (MembershipMethod.RULE, MembershipMethod.RULE, True),
        (MembershipMethod.RULE, MembershipMethod.EMBEDDING, True),
        (MembershipMethod.EMBEDDING, MembershipMethod.RULE, False),
        (MembershipMethod.EMBEDDING, MembershipMethod.LLM, True),
        (MembershipMethod.LLM, MembershipMethod.EMBEDDING, False),
        (MembershipMethod.LLM, MembershipMethod.MANUAL, True),
    ],
)
def test_inactive_membership_reactivation_follows_decision_priority(
    existing: MembershipMethod,
    incoming: MembershipMethod,
    allowed: bool,
) -> None:
    assert may_reactivate_membership(existing, False, incoming) is allowed
