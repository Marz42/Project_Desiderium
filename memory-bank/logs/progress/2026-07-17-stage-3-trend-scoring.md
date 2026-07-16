# Progress: Stage 3 — Metric Snapshots, Baselines & Trend Scoring

**Date:** 2026-07-17 01:52
**Status:** completed

## Summary

Implemented the no-LLM trend discovery core: metric snapshot CRUD with age-based scheduling, channel baselines with confidence levels, capped BreakoutRatio, rule-based entity clustering, composite trend scoring, lifecycle states, daily score snapshots, and cross-day trend ID reuse.

## Deliverables

### Snapshots (P3-01→05)
- [x] `MetricsRepository` with idempotent upsert on `(content_item_id, captured_at_bucket)`
- [x] `SnapshotService` with dynamic scheduling by video age (5h / 10h / 24h intervals from config)
- [x] Incremental view detection and negative-increment anomaly flagging
- [x] Hour-bucket deduplication via `hour_bucket()`
- [x] Scheduled `capture_metric_snapshots` job every 4h

### Baselines (P3-06→11)
- [x] Four age buckets in `app/domain/trend_metrics.py`
- [x] Channel median velocity baselines with sample-size confidence
- [x] Global fallback when channel baseline missing
- [x] `BreakoutRatio` with `min(ratio, capped_breakout_max)` from config
- [x] `BaselinesRepository` + `BaselineService.refresh_channel_baselines()`

### Trends & Scoring (P3-12→23)
- [x] `config/anime_entities.yaml` entity dictionary (17 rules)
- [x] `cluster_videos()` rule-based clustering with multi-channel filter
- [x] `trend_themes` + `trend_members` upsert via `TrendsRepository`
- [x] Composite score: resonance 35%, breakout 25%, momentum 20%, persistence 10%, scale 5%, novelty 5%
- [x] Lifecycle: new / rising / stable / declining / reviving / dormant
- [x] `trend_score_snapshots` table + daily snapshot on pipeline run
- [x] Cross-day trend ID reuse by `entity_id` / `canonical_name` lookup
- [x] All thresholds in `config/scoring.yaml`

## Algorithm Migration

- Core logic moved from `scripts/shadow/scoring.py` → `app/domain/trend_metrics.py`
- Shadow scripts retain backward-compatible `VideoRecord` wrapper
- `app/services/scoring_config.py` loads YAML config with `@lru_cache`

## Tests

28 unit tests passing:
- `tests/unit/test_trend_metrics.py` (7)
- `tests/unit/test_clustering.py` (3)
- `tests/unit/test_lifecycle.py` (3)
- `tests/unit/test_shadow_scoring.py` (5, via compatibility layer)
- Existing Stage 1–2 tests (10)

## Files Added/Modified

- `config/scoring.yaml`, `config/anime_entities.yaml`
- `app/domain/trend_metrics.py`
- `app/services/scoring_config.py`, `baseline.py`, `snapshots.py`, `clustering.py`, `scoring.py`, `lifecycle.py`, `trend_discovery.py`
- `app/repositories/metrics.py`, `baselines.py`, `trends.py`
- `app/jobs/trend_tasks.py`, `app/jobs/scheduler.py`
- `app/models.py` — `TrendScoreSnapshot`
- `migrations/versions/a1b2c3d4e5f6_trend_score_snapshots.py`
- `scripts/shadow/scoring.py` — compatibility re-exports
- `pyproject.toml` — added `pyyaml`

## Notes

- `pd-check-all.py` reports pre-existing OKF lint errors on `mvp-plan.md` and `project-brief.md`; not introduced by this stage.
- Daily trend pipeline scheduled at 01:30 UTC via `run_trend_discovery` cron job.
