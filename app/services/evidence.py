"""Evidence content ID validation for LLM outputs."""

from __future__ import annotations


def validate_evidence_ids(
    evidence_ids: list[str],
    allowed_ids: set[str],
) -> list[str]:
    """Return only IDs present in allowed_ids; empty list if none valid."""
    if not evidence_ids or not allowed_ids:
        return []
    return [cid for cid in evidence_ids if cid in allowed_ids]


def require_evidence_ids(
    evidence_ids: list[str],
    allowed_ids: set[str],
) -> list[str]:
    """Validate and raise if no valid evidence remains."""
    valid = validate_evidence_ids(evidence_ids, allowed_ids)
    if not valid:
        raise ValueError("no valid evidence content IDs in LLM output")
    return valid
