"""Pure precedence rules for trend membership decisions."""

from __future__ import annotations

from app.models import MembershipMethod

_METHOD_PRIORITY: dict[MembershipMethod, int] = {
    MembershipMethod.RULE: 0,
    MembershipMethod.EMBEDDING: 1,
    MembershipMethod.LLM: 2,
    MembershipMethod.MANUAL: 3,
}


def membership_method_priority(method: MembershipMethod) -> int:
    return _METHOD_PRIORITY[method]


def may_reactivate_membership(
    existing_method: MembershipMethod,
    existing_active: bool,
    incoming_method: MembershipMethod,
) -> bool:
    """Return whether an incoming decision may reactivate a membership.

    Manual removals are sticky. Only another explicit manual decision (including
    a validated rollback) may reactivate them.
    """
    if existing_active:
        return True
    if existing_method == MembershipMethod.MANUAL:
        return incoming_method == MembershipMethod.MANUAL
    return membership_method_priority(incoming_method) >= membership_method_priority(
        existing_method
    )
