# Active Task: Stage 2 — Watchlist & YouTube Stable Collection

**Plan:** knowledge/plans/mvp-plan.md (Section: 阶段2)
**Status:** completed
**Started:** 2026-07-17
**Completed:** 2026-07-17 01:47
**Depends on:** Stage 1 ✓

## Objective

Build a sustainable data foundation. Integrate the shadow validation code into proper database-backed services with scheduling.

## Checklist

### Watchlist (P2-01→08)
- [x] watch_items table CRUD
- [x] CSV import with validation
- [x] Tier management (priority/general/experimental)
- [x] Tags and notes
- [x] Enable/disable toggle
- [x] Crawl status display

### YouTube Adapter (P2-09→19)
- [x] Channel ID resolution
- [x] Uploads playlist discovery
- [x] Keyword search
- [x] Batch video details
- [x] API quota tracking
- [x] 429/403/network error handling with exponential backoff
- [x] Raw response preservation (raw_payload JSONB)
- [x] Platform-normalized output
- [x] Idempotent writes (UNIQUE constraint)
- [x] Cursor-based incremental fetching

### Scheduling (P2-20→25)
- [x] Priority channel task: every 4-6h (default 5h)
- [x] General channel task: every 12-24h (default 18h)
- [x] Keyword task: daily
- [x] Manual trigger support
- [x] Failed task retry
- [x] Task mutex

## Next

Stage 3: Metric snapshots, channel baselines, and trend scoring (mvp-plan 阶段3).
