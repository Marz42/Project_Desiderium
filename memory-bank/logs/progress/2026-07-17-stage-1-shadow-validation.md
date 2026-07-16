---
type: paradigma-session-log
title: Stage 1 Shadow Validation and Golden Dataset
description: Session summary for YouTube shadow validation, BreakoutRatio scoring, and golden dataset creation.
tags: [session, stage-1, shadow-validation, golden-dataset]
timestamp: 2026-07-17T01:39:00+08:00
paradigma:
  layer: log
  lifecycle: append-only
  okf_export: optional
  update_policy: append-only
---

# Session Summary

## User Goal

Complete Stage 1 shadow validation: minimal YouTube scraper, 20-30 anime recap channels, BreakoutRatio scoring, manual trend labels, golden dataset CSV/JSON, and validation report proving the algorithm before full backend build.

## Actions Taken

- Curated `scripts/shadow/watchlist.csv` with 28 verified priority/general anime recap channels plus keywords and anime title watches.
- Built `scripts/shadow/youtube_client.py` with file cache, quota tracking, playlistItems.list for uploads, batched videos.list, and ≤10 search.list budget.
- Implemented `scripts/shadow/scoring.py`: age buckets, cold-start velocity, channel median baselines, BreakoutRatio, trend cluster scoring.
- Fetched 389 real videos from 79 channels via YouTube Data API (quota ~1121 units, 10 search calls).
- Created `scripts/shadow/trend_labels.json` with 15 manual trend definitions and manager value labels.
- Built golden dataset (`data/shadow/golden_dataset.csv`, `.json`) with per-video scoring fields.
- Generated `data/shadow/validation_report.md` — Precision@15 60%, recall of high-value trends 100%.
- Added unit tests `tests/unit/test_shadow_scoring.py` (5 tests).
- Updated `app/config.py` to accept `YOUTUBE_DATA_API_KEY` alias.

## Files Read

- `memory-bank/runtime/active-task.md`
- `memory-bank/knowledge/project-brief.md`
- `memory-bank/knowledge/plans/mvp-plan.md`

## Files Created/Modified

- `scripts/shadow/*` (watchlist, client, scoring, fetch, build, validate, pipeline)
- `data/shadow/golden_dataset.csv`, `golden_dataset.json`, `validation_report.md`, `raw_videos.json`, `fetch_meta.json`
- `tests/unit/test_shadow_scoring.py`
- `app/config.py`, `.env.example`, `.gitignore`

## Decisions Accepted

- Shadow validation runs as standalone scripts under `scripts/shadow/` before Stage 2 adapter integration.
- API cache stored in `data/shadow/cache/` (gitignored); golden dataset committed for regression.
- Hindi/manhwa high-resonance false positives documented for Stage 2 calibration.

## Knowledge Updates

- None (operational scripts; domain knowledge deferred to Stage 2).

## Follow-ups

- Stage 2: migrate scoring into `app/services/` and YouTube adapter with DB persistence.
- Add language filter and manager-value penalty to trend scorer.
- Run `pd-archive-task.py --write` to archive completed active task.
