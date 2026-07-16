# Active Task: Stage 3 — Metric Snapshots, Baselines & Trend Scoring

**Status:** completed | **Started:** 2026-07-17 | **Completed:** 2026-07-17 01:52 | **Depends on:** Stage 2 ✓

## Objective
Build the trend discovery core that works without LLM. Snapshots → baseline → BreakoutRatio → clustering → scoring → lifecycle.

## Deliverables
- [x] metric_snapshots table + dynamic scheduling by video age
- [x] Channel baseline (median velocity per age bucket, confidence levels)
- [x] BreakoutRatio with capped values
- [x] Rule-based clustering + trend_themes/trend_members tables
- [x] Cross-channel resonance, relative breakout, momentum, persistence scoring
- [x] Trend lifecycle (new/rising/stable/declining/reviving)
- [x] Daily score snapshots + trend cross-day reuse
- [x] All thresholds in config, not hardcoded

## Reference
Stage 1's scripts/shadow/scoring.py algorithm migrated to `app/domain/trend_metrics.py` and services layer.

## Next
Stage 4: Subtitle layered fetch and LLM semantic analysis.
