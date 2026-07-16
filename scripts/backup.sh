#!/usr/bin/env bash
# PostgreSQL backup for Desiderium (host or Docker sidecar).
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILENAME="desiderium-${TIMESTAMP}.sql.gz"
TARGET="${BACKUP_DIR}/${FILENAME}"

mkdir -p "${BACKUP_DIR}"

echo "[backup] starting dump -> ${TARGET}"

if [[ -n "${DATABASE_URL:-}" ]]; then
  # Convert asyncpg URL to libpq format for pg_dump.
  PGURL="${DATABASE_URL/postgresql+asyncpg/postgresql}"
  pg_dump "${PGURL}" | gzip -9 > "${TARGET}"
else
  : "${PGHOST:?PGHOST or DATABASE_URL required}"
  : "${PGUSER:?PGUSER required}"
  : "${PGDATABASE:?PGDATABASE required}"
  pg_dump | gzip -9 > "${TARGET}"
fi

echo "[backup] wrote ${TARGET} ($(du -h "${TARGET}" | awk '{print $1}'))"

find "${BACKUP_DIR}" -name 'desiderium-*.sql.gz' -type f -mtime +"${RETENTION_DAYS}" -delete
echo "[backup] pruned backups older than ${RETENTION_DAYS} days"
