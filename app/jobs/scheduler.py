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
from app.jobs.ops_tasks import monitor_disk_space, purge_stale_metric_snapshots
from app.jobs.publication_tasks import run_publication_metrics
from app.jobs.semantic_tasks import run_semantic_analysis
from app.jobs.tiktok_tasks import (
    crawl_tiktok_accounts,
    crawl_tiktok_keywords,
    crawl_tiktok_rankings,
    retry_failed_tiktok_crawls,
)
from app.jobs.transcript_tasks import fetch_priority_transcripts
from app.jobs.trend_tasks import capture_metric_snapshots, run_trend_discovery


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
    scheduler.add_job(
        capture_metric_snapshots,
        "interval",
        hours=4,
        id="metric_snapshots",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_trend_discovery,
        "cron",
        hour=1,
        minute=30,
        id="trend_discovery",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        fetch_priority_transcripts,
        "interval",
        hours=6,
        id="transcript_fetch",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_semantic_analysis,
        "cron",
        hour=2,
        minute=0,
        id="semantic_analysis",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    if settings.tiktok_enabled:
        scheduler.add_job(
            crawl_tiktok_accounts,
            "interval",
            hours=settings.tiktok_crawl_hours,
            id="crawl_tiktok_accounts",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.add_job(
            crawl_tiktok_keywords,
            "interval",
            hours=settings.tiktok_crawl_hours,
            id="crawl_tiktok_keywords",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.add_job(
            crawl_tiktok_rankings,
            "interval",
            hours=settings.tiktok_crawl_hours,
            id="crawl_tiktok_rankings",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.add_job(
            retry_failed_tiktok_crawls,
            "interval",
            hours=settings.tiktok_retry_hours,
            id="crawl_tiktok_retry",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    scheduler.add_job(
        run_publication_metrics,
        "interval",
        hours=2,
        id="publication_metrics",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        purge_stale_metric_snapshots,
        "cron",
        hour=3,
        minute=30,
        id="snapshot_retention",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        monitor_disk_space,
        "interval",
        hours=1,
        id="disk_monitor",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
