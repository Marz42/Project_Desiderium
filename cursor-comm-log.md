# Cursor Communication Log — Project Desiderium

## Stage 0 — Engineering Baseline
**Commit:** 5f6786f | **Tests:** 3 | **Status:** ✅

Cursor produced:
- pyproject.toml with FastAPI, SQLAlchemy async, Alembic, httpx, Pydantic, APScheduler, pytest
- app/main.py — FastAPI with lifespan and structured JSON logging
- app/config.py — Pydantic Settings from .env
- app/db.py — async engine, session factory, health check
- app/domain/interfaces.py — SourceAdapter + TranscriptAdapter ABCs
- app/models.py — all 13 tables: watch_items, content_items, metric_snapshots, transcripts, channel_baselines, trend_themes, trend_members, creative_angles, daily_candidates, briefs, brief_items, publication_records, crawl_jobs
- Package init files for adapters/, services/, web/, repositories/, jobs/, schemas/
- app/web/routes/health.py — /health/live, /health/ready (DB-aware)
- app/worker.py — APScheduler heartbeat worker
- Dockerfile — multi-stage Python 3.12
- docker-compose.yml — web (8000), worker, postgres:16 with healthcheck
- alembic.ini + migrations/env.py — async PostgreSQL migrations
- .env.example, updated .gitignore
- tests/conftest.py + tests/test_health.py — 3/3 passing

---

## Stage 1 — Shadow Validation & Golden Dataset
**Commit:** ed4e328 | **Tests:** 8 | **Status:** ✅

Cursor produced:
- scripts/shadow/watchlist.csv — 28 channels + keywords/anime
- scripts/shadow/youtube_client.py — YouTube scraper (cache, quota-aware)
- scripts/shadow/fetch_videos.py — video fetching pipeline
- scripts/shadow/scoring.py — age buckets, velocity, baseline, BreakoutRatio
- scripts/shadow/trend_labels.json — manual trend labels
- scripts/shadow/run_pipeline.py — end-to-end pipeline
- data/shadow/golden_dataset.csv + .json — 389 videos from 79 channels
- data/shadow/validation_report.md

Results: Precision@15 = 60%, High-value recall = 100%
API usage: ~1,121 quota units, 10 search.list calls (at budget cap)
Top trends: One Piece, JJK, Solo Leveling, Chainsaw Man

---

## Stage 2 — Watchlist & YouTube Stable Collection
**Commit:** 442457a | **Tests:** 18 | **Status:** ✅

Cursor produced:
- Watchlist CRUD at /watchlist — list, create, edit, delete, CSV import
- YouTube Adapter (app/adapters/youtube/) — async client, implements SourceAdapter
- Channel resolution, uploads playlist, keyword search, batch videos.list
- Quota tracking (10k daily / 100 search calls), exponential backoff
- Scheduling jobs: crawl_priority (5h), crawl_general (18h), crawl_keywords (daily 06:00), crawl_retry (hourly)
- Mutex: in-process lock + PostgreSQL advisory lock
- crawl_jobs tracking table

---

## Stage 3 — Metric Snapshots, Baselines & Trend Scoring
**Commit:** cd13841 | **Tests:** 28 | **Status:** ✅

Cursor produced:
- config/scoring.yaml — weights, breakout caps, lifecycle ratios
- config/anime_entities.yaml — 17 rule-based entity definitions
- app/domain/trend_metrics.py — age buckets, velocity, baselines, capped BreakoutRatio
- app/services/snapshots.py — CRUD, hour-bucket idempotency
- app/services/baseline.py — channel median velocity, confidence levels
- app/services/clustering.py — keyword matching, multi-channel filter
- app/services/scoring.py — 35/25/20/10/5/5 composite
- app/services/lifecycle.py — new/rising/stable/declining/reviving
- app/services/trend_discovery.py — daily orchestration with cross-day trend ID reuse
- Jobs: capture_metric_snapshots (4h), run_trend_discovery (daily 01:30)

---

## Stage 4 — Subtitle & LLM Semantic Analysis
**Commit:** 0b2470d | **Tests:** 43 | **Status:** ✅

Cursor produced:
- app/services/transcripts.py — state machine, public captions, ASR interface
- app/adapters/llm/ — OpenAI-compatible client, JSON Schema output, retry+timeout, token tracking
- config/prompts/ — 5 versioned prompt templates
- app/services/semantic_analysis.py — title translation, trend naming, why-trending, creative angles
- app/services/evidence.py — all LLM outputs must reference real content UUIDs
- app/services/angle_dedup.py — Jaccard + fingerprint semantic dedup
- Jobs: fetch_priority_transcripts (6h), run_semantic_analysis (daily 02:00)
- LLM defaults to gpt-4o-mini, provider-agnostic

---

## Stage 5+6 — Admin Backend + Brief Export + Status Machine
**Commit:** c37876c | **Tests:** 57 | **Status:** ✅

Cursor produced:
- /candidates — 30 directions grouped by trend, filterable (lifecycle/anime/shorts/long/priority)
- /trends/{id} — score timeline, components, member videos, channel distribution
- /history — browse by date, status filters
- /brief — reorder, edit notes, Markdown/HTML export
- /watchlist — enhanced with CSRF
- /login — single-manager auth with signed session cookie
- status machine: candidate → selected → adopted → published, reusable, blocked
- angle_status_audits table for audit trail
- Jinja2 + HTMX + Tailwind CDN (no React)

---

## Stage 7 — TikTok Experiment Adapter
**Commit:** 57eabab | **Tests:** 68 | **Status:** ✅

Cursor produced:
- app/adapters/tiktok/ — TikTokAdapter implementing SourceAdapter
- Account, keyword, and ranking scraping endpoints
- Cookie via TIKTOK_COOKIE env var (never in git, redacted in logs)
- Cookie expiry detection + selector version isolation
- TikTokIngestionService — separate from YouTube ingestion
- TikTok tasks with own mutex locks (1101-1104)
- Global TIKTOK_ENABLED=false by default
- YouTube crawl_tasks.py / trend pipeline unchanged
- Source confidence: YouTube=high, TikTok=low

---

## Stage 8 — Deployment, Stability & Ops
**Commit:** 19a7ec9 | **Tests:** 75 | **Status:** ✅

Cursor produced:
- Dockerfile.prod — production image with 2 uvicorn workers
- docker-compose.prod.yml — postgres, web, worker, Caddy HTTPS
- scripts/backup.sh + scripts/restore.sh — pg_dump flow
- OPS.md + RECOVERY.md — operations and failure recovery runbooks
- GET /health — DB, disk, worker heartbeat
- GET /admin/status — 24h task failures, youtube_quota_usage, LLM cost, snapshot stats
- worker_heartbeats, api_quota_daily, llm_usage_logs tables
- snapshot_retention job (daily 03:30), disk_monitor (hourly)
- config/logrotate.desiderium
- VERSION bumped to 0.7.0

---

**MVP Complete** — 2026-07-17 03:30 — 75 tests, all 8 stages
