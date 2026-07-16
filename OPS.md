# Desiderium Operations Manual

Production deployment, monitoring, and day-to-day operations for the anime trend intelligence stack.

## Architecture (production)

```text
Internet → Caddy (HTTPS) → web (FastAPI) → PostgreSQL
                              ↑
                         worker (APScheduler jobs)
```

- **Docker (primary):** `docker-compose.prod.yml` with `web`, `worker`, `postgres`, and `caddy`.
- **Host (optional):** `deploy/systemd/*.service` units behind your own reverse proxy.

## First-time deploy

1. Copy `.env.example` → `.env` and set secrets (never commit `.env`):
   - `POSTGRES_PASSWORD`, `SECRET_KEY`, `MANAGER_PASSWORD`
   - `YOUTUBE_DATA_API_KEY`, `LLM_API_KEY` (if semantic analysis enabled)
   - `DOMAIN`, `ACME_EMAIL` for HTTPS
2. Create backup directory: `mkdir -p backups`
3. Start stack:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

4. Verify health:

```bash
curl -sS "https://${DOMAIN}/health" | jq .
curl -sS -u manager "https://${DOMAIN}/admin/status"   # after login session
```

5. Enable daily backups (optional profile):

```bash
docker compose -f docker-compose.prod.yml --profile backup up -d backup
```

## Environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `DOMAIN` | Public hostname for Caddy TLS | — |
| `POSTGRES_PASSWORD` | DB password | required in prod |
| `MANAGER_PASSWORD` | Single-manager admin login | empty = auth off |
| `SNAPSHOT_RETENTION_DAYS` | Purge `metric_snapshots` older than N days | 90 |
| `DISK_WARN_PERCENT` | Disk warning threshold | 85 |
| `BACKUP_RETENTION_DAYS` | Local backup retention | 14 |
| `WORKER_STALE_MINUTES` | Worker considered stale after N minutes | 15 |
| `YOUTUBE_DAILY_QUOTA_LIMIT` | YouTube API unit budget | 10000 |

## Monitoring endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /health/live` | No | Liveness probe |
| `GET /health/ready` | No | DB connectivity |
| `GET /health` | No | DB + disk + worker heartbeat |
| `GET /admin/status` | Yes | Ops dashboard JSON |

### `/admin/status` payload highlights

- `task_failures_24h` — failed crawl jobs by adapter
- `youtube_quota_usage` — persisted daily quota from worker crawls
- `llm_usage_today` — token counts and estimated USD cost
- `metric_snapshots` — total rows and retention policy
- `disk` — filesystem usage on `/`

## Scheduled maintenance jobs

| Job | Schedule | Action |
|-----|----------|--------|
| `snapshot_retention` | Daily 03:30 UTC | Delete snapshots older than retention |
| `disk_monitor` | Hourly | Log warning + heartbeat when disk high |
| `backup` (profile) | Daily | `scripts/backup.sh` via sidecar |

## Backups

Manual backup:

```bash
./scripts/backup.sh
# or inside compose:
docker compose -f docker-compose.prod.yml exec postgres /backup.sh
```

Restore (destructive — see [RECOVERY.md](RECOVERY.md)):

```bash
./scripts/restore.sh backups/desiderium-YYYYMMDDTHHMMSSZ.sql.gz --yes
```

## Log rotation

Install on host deployments:

```bash
sudo cp config/logrotate.desiderium /etc/logrotate.d/desiderium
```

Docker deployments rely on container log drivers; redirect app logs to `/var/log/desiderium/` if file rotation is required.

## Database index maintenance

Run after large data growth or slow queries:

```bash
DATABASE_URL=postgresql+asyncpg://... python scripts/optimize_db_indexes.py
```

Runs `ANALYZE` and creates hot-path indexes (`metric_snapshots`, failed `crawl_jobs`, etc.).

## Disk monitoring

```bash
./scripts/disk_monitor.sh /
```

Exits non-zero when usage exceeds `DISK_WARN_PERCENT` — suitable for cron or alerting hooks.

## Secret management

- All secrets live in `.env` only; `.env` is gitignored.
- Rotate `SECRET_KEY` and `MANAGER_PASSWORD` together (sessions invalidate).
- TikTok cookies and API keys must never appear in git or logs.

## Upgrades

```bash
git pull
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

Migrations run automatically on `web` and `worker` startup via `alembic upgrade head`.

## Systemd (host)

1. Install app to `/opt/desiderium`, venv at `/opt/desiderium/.venv`
2. Place env at `/etc/desiderium/desiderium.env`
3. `sudo cp deploy/systemd/*.service /etc/systemd/system/`
4. `sudo systemctl enable --now desiderium-web desiderium-worker`

Place Caddy or nginx in front of `127.0.0.1:8000` for TLS.
