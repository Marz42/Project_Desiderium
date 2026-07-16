# Desiderium Failure Recovery Guide

Step-by-step recovery for common production failures. Always snapshot current state before destructive actions.

## Quick diagnostics

```bash
# Stack status
docker compose -f docker-compose.prod.yml ps

# Health
curl -sS "https://${DOMAIN}/health" | jq .

# Ops dashboard (authenticated)
curl -sS -b cookies.txt "https://${DOMAIN}/admin/status" | jq .

# Recent worker logs
docker compose -f docker-compose.prod.yml logs --tail=200 worker
```

## Database unavailable

**Symptoms:** `/health/ready` returns 503; `database: down`.

1. Check Postgres container: `docker compose -f docker-compose.prod.yml logs postgres`
2. Verify disk space: `./scripts/disk_monitor.sh /`
3. Restart Postgres: `docker compose -f docker-compose.prod.yml restart postgres`
4. If data corruption suspected, restore from backup (below).

## Worker stale / jobs not running

**Symptoms:** `/health` shows `worker.stale: true`; no new crawls.

1. Inspect worker logs for exceptions or mutex skips.
2. Restart worker: `docker compose -f docker-compose.prod.yml restart worker`
3. Confirm heartbeat: `worker.last_seen_at` in `/admin/status` updates within 5 minutes.
4. Check for stuck advisory locks (rare): restart worker and postgres if a job hung mid-run.

## YouTube quota exhausted

**Symptoms:** `youtube_quota_usage.exhausted: true` in `/admin/status`; keyword crawls skipped.

1. Wait for Google quota reset (midnight Pacific Time).
2. Reduce `YOUTUBE_MAX_SEARCH_CALLS` if search-heavy.
3. Channel crawls may continue until unit budget is hit — prioritize `PRIORITY` tier watch items.

## LLM / semantic analysis failures

**Symptoms:** `llm_failures` in worker logs; trends lack Chinese summaries.

1. Verify `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` in `.env`.
2. Check `llm_usage_today` for spikes — adjust `LLM_COST_PER_MILLION_*` estimates if needed.
3. Semantic failures are non-blocking; scoring and crawls continue.

## Disk full

**Symptoms:** `disk.status: warn` in `/health`; backup or Postgres errors.

1. Run `./scripts/disk_monitor.sh /`
2. Prune old backups: `find backups -name '*.sql.gz' -mtime +14 -delete`
3. Trigger snapshot retention early:

```bash
docker compose -f docker-compose.prod.yml exec worker python -c "
import asyncio
from app.db import get_session_factory
from app.services.snapshot_retention import purge_old_snapshots
async def main():
    async with get_session_factory()() as s:
        print(await purge_old_snapshots(s))
        await s.commit()
asyncio.run(main())
"
```

4. Expand volume or move `postgres_data` to larger disk.

## Restore database from backup

**Warning:** Overwrites current database contents.

1. Stop writers:

```bash
docker compose -f docker-compose.prod.yml stop web worker
```

2. Restore:

```bash
./scripts/restore.sh backups/desiderium-YYYYMMDDTHHMMSSZ.sql.gz --yes
```

3. Run migrations (idempotent):

```bash
docker compose -f docker-compose.prod.yml run --rm web alembic upgrade head
```

4. Start services:

```bash
docker compose -f docker-compose.prod.yml up -d web worker
```

## Full stack rebuild (keep data volume)

```bash
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build
```

Postgres data persists in `postgres_data` volume unless explicitly removed.

## Caddy / HTTPS issues

1. Confirm `DOMAIN` DNS points to host.
2. Check Caddy logs: `docker compose -f docker-compose.prod.yml logs caddy`
3. Ensure ports 80/443 are open for ACME HTTP-01 challenge.
4. Set valid `ACME_EMAIL` for certificate notifications.

## When to escalate

- Repeated restore failures → verify backup integrity with `gunzip -t backup.sql.gz`
- Postgres won't start after disk recovery → consult PostgreSQL WAL recovery docs
- Data loss with no backups → re-seed watchlist and accept metric history gap

## Post-incident checklist

- [ ] `/health` and `/admin/status` green
- [ ] Worker heartbeat fresh
- [ ] Manual crawl on one watch item succeeds
- [ ] Document incident in `memory-bank/knowledge/known-issues/` if recurring
