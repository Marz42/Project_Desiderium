# Active Task: Stage 7 — TikTok Experiment Adapter

**Status:** completed | **Depends on:** Stage 5 ✓

## Objective
Isolated experimental adapter. Must NOT affect YouTube pipeline.

## Deliverables
- [x] TikTokAdapter implementing SourceAdapter
- [x] Account scraping, keyword scraping, public list/tag scraping
- [x] Cookie management via `TIKTOK_COOKIE` env var (not in git)
- [x] Cookie expiry detection
- [x] Page structure version isolation (`config/tiktok.yaml`, selector v1)
- [x] Normalized output matching content_items schema
- [x] Source confidence: YouTube=high, TikTok=low
- [x] Independent worker tasks + isolated failure/retry
- [x] Global on/off toggle (`TIKTOK_ENABLED`, default false)
- [x] Failure alerting + crawl_job logging

## Notes
- No stability guarantee — experimental per MVP spec.
- TikTok jobs only registered when `TIKTOK_ENABLED=true`.
- YouTube crawl/retry/trend pipeline unchanged.
