#!/usr/bin/env python3
"""Analyze PostgreSQL tables and apply recommended index maintenance."""

from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

INDEX_STATEMENTS = [
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_metric_snapshots_content_captured "
    "ON metric_snapshots (content_item_id, captured_at)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_crawl_jobs_finished_at "
    "ON crawl_jobs (finished_at DESC) WHERE status = 'failed'",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_content_items_published_at "
    "ON content_items (published_at DESC)",
    "ANALYZE metric_snapshots",
    "ANALYZE crawl_jobs",
    "ANALYZE content_items",
    "ANALYZE trend_themes",
    "ANALYZE llm_usage_logs",
]


async def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 1

    engine = create_async_engine(database_url, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        for stmt in INDEX_STATEMENTS:
            print(f"executing: {stmt}")
            await conn.execute(text(stmt))

        result = await conn.execute(
            text(
                """
                SELECT relname, seq_scan, idx_scan, n_live_tup
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                ORDER BY seq_scan DESC
                LIMIT 10
                """
            )
        )
        print("top sequential scan tables:")
        for row in result:
            print(
                f"  {row.relname}: seq_scan={row.seq_scan} idx_scan={row.idx_scan} rows={row.n_live_tup}"
            )

    await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
