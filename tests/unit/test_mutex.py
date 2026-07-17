"""Regression tests for job-level advisory lock allocation."""

from __future__ import annotations

import pytest

from app.jobs.mutex import LOCK_IDS, release_batch_mutex


def test_transcript_and_semantic_jobs_have_distinct_locks() -> None:
    assert LOCK_IDS["transcript_fetch"] != LOCK_IDS["semantic_analysis"]
    assert len(LOCK_IDS.values()) == len(set(LOCK_IDS.values()))


@pytest.mark.asyncio
async def test_unknown_job_name_does_not_fall_back_to_shared_lock() -> None:
    with pytest.raises(KeyError):
        await release_batch_mutex(None, "unknown_job")  # type: ignore[arg-type]
