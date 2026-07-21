---
type: paradigma-progress-log
title: Fix snapshot logging KeyError and trend discovery MissingGreenlet
timestamp: 2026-07-21T10:01:00+08:00
tags: [progress, bugfix, pipeline, sqlalchemy, logging]
paradigma:
  layer: logs
  temperature: cold
  lifecycle: append-only
---

# 2026-07-21 Pipeline snapshot / MissingGreenlet fixes

## Changes

1. **`app/services/snapshots.py`**: rename summary key `created` → `snapshots_created` so `logger.info(..., extra={**summary})` no longer overwrites `LogRecord.created`.
2. **`app/repositories/metrics.py`**: `list_content_for_baseline` eager-loads `ContentItem.metric_snapshots` via `selectinload`, fixing async lazy-load `MissingGreenlet` in `velocities_from_content_items` / `_latest_views`.

## Verification

| Check | Result |
|-------|--------|
| `capture_metric_snapshots` | OK（exit 0，无 KeyError） |
| `run_trend_discovery` | OK（exit 0，无 MissingGreenlet；ONNX 缺 `sentence_transformers` 警告仍在） |
| `pytest tests/ -v --tb=short` | **152 passed, 8 skipped** |

## DB after fix run

| Entity | Count |
|--------|------:|
| content_items | 149 |
| metric_snapshots | 4 |
| channel_baselines | 2（此前 0） |
| trend_themes | 0 |
| creative_angles | 0 |

`trend_themes=0` 是聚类阈值/数据问题，不是本次崩溃回归。
