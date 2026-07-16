# Progress: Stage 2 — Watchlist & YouTube Stable Collection

**Date:** 2026-07-17 01:47
**Status:** completed

## Summary

Implemented Stage 2 deliverables: watchlist CRUD with CSV import, YouTube `SourceAdapter`, scheduled crawl jobs with mutex/retry, `crawl_jobs` tracking, and HTMX web UI for watchlist management.

## Deliverables

### Watchlist (P2-01→08)
- [x] `WatchlistRepository` + `WatchlistService` CRUD
- [x] CSV import with validation and duplicate detection
- [x] Tier management (priority/general/experimental)
- [x] Tags and notes
- [x] Enable/disable toggle
- [x] Crawl status display (last_success_at, last_status, consecutive_failures)

### YouTube Adapter (P2-09→19)
- [x] Async `YouTubeClient` migrated from `scripts/shadow/youtube_client.py`
- [x] `YouTubeAdapter` implementing `SourceAdapter` interface
- [x] Channel ID resolution, uploads playlist, keyword search
- [x] Batch video details (50 IDs)
- [x] API quota tracking with daily limit + search call budget
- [x] 429/403/network exponential backoff
- [x] Raw response preservation in `content_items.raw_payload`
- [x] Platform-normalized output via `normalize.py`
- [x] Idempotent upsert on `UNIQUE(platform, external_id)`
- [x] Cursor-based incremental fetching via `config.page_token`

### Scheduling (P2-20→25)
- [x] Priority channel task: every 5h (configurable 4-6h)
- [x] General channel task: every 18h (configurable 12-24h)
- [x] Keyword task: daily cron
- [x] Manual trigger via web UI and `crawl_single_item`
- [x] Failed task retry (hourly, max 3 retries)
- [x] Task mutex: in-process lock + PostgreSQL advisory lock + DB running-batch check

### Web UI
- [x] `/watchlist` list with tier/enabled filters
- [x] Create/edit/delete watch items
- [x] CSV import page
- [x] Per-item crawl trigger and job history

## Tests

18 tests passing:
- `tests/unit/test_watchlist_csv.py`
- `tests/unit/test_youtube_normalize.py`
- `tests/unit/test_youtube_adapter.py`
- Existing health tests

## Files Added/Modified

- `app/adapters/youtube/` — client, adapter, normalize
- `app/repositories/watchlist.py`, `content.py`
- `app/services/watchlist.py`, `ingestion.py`
- `app/jobs/crawl_tasks.py`, `mutex.py`, `scheduler.py`
- `app/web/routes/watchlist.py`, `app/web/templates/`
- `app/config.py`, `app/worker.py`, `app/main.py`
- `.env.example`, `pyproject.toml`

## Notes

- `pd-check-all.py` reports pre-existing OKF lint errors on `mvp-plan.md` and `project-brief.md` (missing frontmatter); not introduced by this stage.
- Quota exhaustion gracefully skips keyword/anime searches while channel crawls continue until quota hit.
