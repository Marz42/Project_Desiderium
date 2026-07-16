"""Register APScheduler jobs for crawl tasks."""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import Settings
from app.jobs.crawl_tasks import (
    crawl_general_channels,
    crawl_keywords,
    crawl_priority_channels,
    retry_failed_crawls,
)


def register_crawl_jobs(scheduler: AsyncIOScheduler, settings: Settings) -> None:
    scheduler.add_job(
        crawl_priority_channels,
        "interval",
        hours=settings.crawl_priority_hours,
        id="crawl_priority",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        crawl_general_channels,
        "interval",
        hours=settings.crawl_general_hours,
        id="crawl_general",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        crawl_keywords,
        "cron",
        hour=settings.crawl_keyword_hour,
        minute=0,
        id="crawl_keywords",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        retry_failed_crawls,
        "interval",
        hours=1,
        id="crawl_retry",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
