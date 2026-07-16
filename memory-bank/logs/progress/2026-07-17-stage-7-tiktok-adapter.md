# Progress: Stage 7 — TikTok Experiment Adapter

**Date:** 2026-07-17 02:06 | **Stage:** 7

## Summary

Implemented an isolated experimental TikTok adapter. TikTok failures are contained in a separate ingestion service, worker tasks, and retry loop — YouTube crawl, metrics, and trend discovery are unchanged.

## Deliverables

- [x] `TikTokAdapter` implementing `SourceAdapter` (`app/adapters/tiktok/`)
- [x] Account, keyword, and tag/list (ranking) scraping via cookie-authenticated HTTP
- [x] `TIKTOK_COOKIE` env var; redacted from logs; documented in `.env.example`
- [x] Cookie expiry detection (login markers, HTTP 401/403, redirect URLs)
- [x] Selector version isolation (`config/tiktok.yaml`, `selectors.py` v1)
- [x] `normalize_tiktok_video()` → content_items schema + `source_confidence: low`
- [x] YouTube normalize adds `source_confidence: high`; `app/domain/source_confidence.py`
- [x] `TikTokIngestionService` + `app/jobs/tiktok_tasks.py` (separate mutex/retry)
- [x] `TIKTOK_ENABLED` global toggle (default off); scheduler registers TikTok jobs only when enabled
- [x] Failure alerting via structured ERROR logs + `crawl_jobs` records
- [x] Unit tests: adapter, normalize, source confidence (14 new assertions, 68 total pass)

## Key Files

| Area | Path |
|------|------|
| Adapter | `app/adapters/tiktok/` |
| Ingestion | `app/services/tiktok_ingestion.py` |
| Worker | `app/jobs/tiktok_tasks.py` |
| Config | `config/tiktok.yaml`, `app/config.py` |
| Confidence | `app/domain/source_confidence.py`, `config/scoring.yaml` |

## Verification

```bash
python -m pytest -q   # 68 passed
```
