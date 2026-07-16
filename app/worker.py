"""APScheduler-based background worker for crawl and analysis jobs."""

from __future__ import annotations

import asyncio
import logging
import signal

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.db import check_database_connection, dispose_engine, get_session_factory
from app.jobs.scheduler import register_crawl_jobs
from app.logging_config import configure_logging

logger = logging.getLogger(__name__)


async def heartbeat() -> None:
    db_ok = await check_database_connection()
    logger.info(
        "Worker heartbeat",
        extra={
            "service": "worker",
            "component": "heartbeat",
            "database": "up" if db_ok else "down",
        },
    )
    session_factory = get_session_factory()
    async with session_factory() as session:
        from app.repositories.ops import OpsRepository

        repo = OpsRepository(session)
        await repo.upsert_heartbeat(
            "worker",
            details={"database": "up" if db_ok else "down"},
        )
        await session.commit()


async def run_worker() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "Starting worker",
        extra={"service": "worker", "component": "main", "environment": settings.environment},
    )

    scheduler = AsyncIOScheduler()
    scheduler.add_job(heartbeat, "interval", minutes=5, id="heartbeat", replace_existing=True)
    register_crawl_jobs(scheduler, settings)
    scheduler.start()
    await heartbeat()

    stop_event = asyncio.Event()

    def _handle_signal(*_: object) -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)

    await stop_event.wait()
    scheduler.shutdown(wait=False)
    await dispose_engine()
    logger.info("Worker stopped", extra={"service": "worker", "component": "main"})


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
