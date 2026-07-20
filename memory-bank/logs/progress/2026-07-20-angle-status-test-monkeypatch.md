---
type: paradigma-progress-log
title: Angle status test monkeypatch fix
description: Fixed unit test that was calling real YouTube API due to incorrect mock target.
tags: [progress, test, g4]
timestamp: 2026-07-20T17:17:00+08:00
paradigma:
  layer: logs
  temperature: cold
  lifecycle: archival
  okf_export: false
---

# Angle status test monkeypatch fix

## Summary

Fixed `test_publish_with_valid_youtube_url_creates_retryable_publication_record` in `tests/unit/test_angle_status.py`.

## Root cause

The test patched `app.services.publication_metrics.get_settings` to return `Settings(youtube_api_key="")`, but pydantic-settings still loads `YOUTUBE_API_KEY` from `.env`, so `_build_adapter()` created a real YouTube client and the test hit the live API.

## Fix

Monkeypatch `PublicationMetricsService._build_adapter` to return `None`, matching the no-API-key path in `attempt_immediate_capture` and leaving `fetch_status=PENDING`.

## Verification

`pytest tests/unit/test_angle_status.py` — 13 passed.
