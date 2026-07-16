# Progress: Stage 8 — Deployment, Stability & Ops

**Date:** 2026-07-17 02:10  
**Status:** completed

## Summary

Implemented production deployment stack, operational monitoring, backup/restore tooling, and runbooks.

## Delivered

### Deployment
- `Dockerfile.prod` — production image with postgresql-client, backup dir, 2 uvicorn workers
- `docker-compose.prod.yml` — postgres, web, worker, Caddy HTTPS, optional backup sidecar
- `deploy/caddy/Caddyfile` — automatic TLS via Let's Encrypt
- `deploy/systemd/desiderium-{web,worker}.service` — host deployment option

### Ops data layer
- Migration `c8d9e0f1a2b3`: `worker_heartbeats`, `api_quota_daily`, `llm_usage_logs`
- Composite index `ix_metric_snapshots_content_captured`
- `app/repositories/ops.py`, services for health, quota, LLM usage, snapshot retention, admin status

### API
- `GET /health` — database, disk, worker heartbeat
- `GET /admin/status` — task failures (24h), YouTube quota, LLM cost today, snapshot stats

### Worker jobs
- Worker heartbeat persisted to DB every 5 min
- YouTube quota persisted after crawl/snapshot batches
- LLM usage recorded per semantic analysis call
- `snapshot_retention` daily cron (03:30 UTC)
- `disk_monitor` hourly

### Scripts & docs
- `scripts/backup.sh`, `scripts/restore.sh`, `scripts/disk_monitor.sh`, `scripts/optimize_db_indexes.py`
- `config/logrotate.desiderium`
- `OPS.md`, `RECOVERY.md`

## Tests

75 passed (added `test_health_expanded`, `test_admin_status`, `test_system_health`, `test_llm_usage`).

## Notes

- `pd-check-all.py` still fails on pre-existing OKF frontmatter gaps in `mvp-plan.md` / `project-brief.md` (not introduced this stage).
