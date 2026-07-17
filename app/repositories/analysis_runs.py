"""Persistence for reproducible analysis-run metadata."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnalysisRun


class AnalysisRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def start(
        self,
        *,
        run_date: date,
        run_kind: str,
        scoring_version: str | None,
        algorithm_version: str,
        config_hash: str,
        run_fingerprint: str,
        config_snapshot: dict[str, Any],
        prompt_versions: dict[str, str],
        analysis_run_id: uuid.UUID | None = None,
    ) -> AnalysisRun:
        run_id = analysis_run_id or uuid.uuid4()
        row = await self._session.get(AnalysisRun, run_id)
        if row is None:
            row = AnalysisRun(
                id=run_id,
                run_date=run_date,
                run_kind=run_kind,
                scoring_version=scoring_version,
                algorithm_version=algorithm_version,
                config_hash=config_hash,
                run_fingerprint=run_fingerprint,
                config_snapshot=config_snapshot,
                prompt_versions=prompt_versions,
                started_at=datetime.now(UTC),
            )
            self._session.add(row)
        else:
            if row.run_fingerprint != run_fingerprint:
                raise ValueError("analysis_run_id cannot be reused with a different fingerprint")
            row.scoring_version = scoring_version
            row.algorithm_version = algorithm_version
            row.config_hash = config_hash
            row.config_snapshot = config_snapshot
            row.prompt_versions = prompt_versions
            row.started_at = datetime.now(UTC)
            row.finished_at = None
            row.summary = None
        await self._session.flush()
        return row

    async def finish(self, row: AnalysisRun, summary: dict[str, Any]) -> None:
        row.finished_at = datetime.now(UTC)
        row.summary = summary
        await self._session.flush()
