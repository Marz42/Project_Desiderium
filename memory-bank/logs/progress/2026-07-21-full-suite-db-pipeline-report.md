---
type: paradigma-progress-log
title: Full suite + DB + pipeline verification report
timestamp: 2026-07-21T09:55:00+08:00
tags: [progress, testing, pipeline, verification]
paradigma:
  layer: logs
  temperature: cold
  lifecycle: append-only
---

# 2026-07-21 Full suite / DB / pipeline report

## Scope

Report-only verification against live PostgreSQL (`localhost:5432/desiderium`). No code fixes.

## Results

### Tests

- Full suite (`DATABASE_URL=... pytest tests/ -v`): **152 passed, 8 skipped** (integration gated on `RUN_INTEGRATION_TESTS!=1`).
- Integration (`RUN_INTEGRATION_TESTS=1`): **7 passed, 1 failed**
  - Failed: `test_publish_without_api_key_persists_retryable_enriched_record`
  - Expected `PublicationFetchStatus.PENDING`, got `FAILED`
  - Warning: MissingGreenlet during immediate publication capture

### Code quality

- `python3 -m compileall app/`: OK
- `scripts/check_migration_head.py`: OK (`a7b8c9d0e1f2`)
- `alembic current` / `heads`: both at `a7b8c9d0e1f2 (head)`

### Database (after pipeline attempt)

| Entity | Count |
|--------|------:|
| watch_items | 29 |
| content_items | 149 (was 75) |
| crawl_jobs | 14 (all SUCCESS, DISCOVER) |
| metric_snapshots | 4 |
| channel_baselines | 0 |
| trend_themes / members / angles / candidates | 0 |

### Pipeline

1. `crawl_priority_channels`: success; content 75→149; +7 crawl_jobs
2. `capture_metric_snapshots`: wrote 4 snapshots; then failed logging with `KeyError: Attempt to overwrite 'created' in LogRecord`
3. `run_trend_discovery`: failed with `MissingGreenlet` lazy-loading `item.metric_snapshots` in baseline refresh; no new trends generated
4. Warning: local ONNX embedding unavailable (`No module named 'sentence_transformers'`)

Priority CHANNEL watch items (7/7) last_status=SUCCESS. Six PRIORITY KEYWORD items remain uncrawled (crawl_priority only covers channel/account).
