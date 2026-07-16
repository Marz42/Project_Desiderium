# Active Task: Stage 1 — Shadow Validation & Golden Dataset

**Plan:** knowledge/plans/mvp-plan.md (Section: 阶段1)
**Status:** completed
**Started:** 2026-07-17
**Completed:** 2026-07-17 01:39
**Depends on:** Stage 0 ✓
**Cursor Mode:** auto

## Objective

Before building the full backend, prove that "cross-channel resonance × relative channel performance" can reproduce the manager's judgment. Build a minimal YouTube scraper, compute BreakoutRatio, manually label trends, and validate scoring against human judgment.

## Deliverables Checklist

- [x] P1-01: Compile 20-30 priority YouTube channels (28 verified anime recap channels)
- [x] P1-02: Compile general channels, keywords, anime titles (watchlist.csv)
- [x] P1-03: Minimal YouTube scraping script (scripts/shadow/youtube_client.py)
- [x] P1-04: Fetch recent videos + current stats (389 videos, 79 channels)
- [x] P1-05: Simplified age buckets (0-6h, 6-24h, 24-72h, 3-7d)
- [x] P1-06: Cold-start velocity estimation
- [x] P1-07: Initial channel baseline (median of recent videos)
- [x] P1-08: BreakoutRatio computation
- [x] P1-09: Manually label videos into trend groups (trend_labels.json)
- [x] P1-10: Manager value labels (high/normal/low per trend)
- [x] P1-11: Build Golden Dataset (data/shadow/golden_dataset.csv + .json)
- [x] P1-12: Validation report (data/shadow/validation_report.md)

## Key Outputs

| Artifact | Path |
|----------|------|
| Watchlist | `scripts/shadow/watchlist.csv` |
| Scraper | `scripts/shadow/fetch_videos.py` |
| Scoring | `scripts/shadow/scoring.py` |
| Golden CSV | `data/shadow/golden_dataset.csv` |
| Golden JSON | `data/shadow/golden_dataset.json` |
| Validation | `data/shadow/validation_report.md` |
| Pipeline | `scripts/shadow/run_pipeline.py` |

## Validation Summary

- 389 videos, 79 channels, 10 labeled trends
- Precision@15: 60%, Recall high-value: 100%
- One Piece, JJK, Solo Leveling rank top; cross-channel resonance detected
- Known gap: Hindi/manhwa clusters score high on resonance — calibrate in Stage 2

## Next

Stage 2: Watchlist DB + stable YouTube ingestion adapter
