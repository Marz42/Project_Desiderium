#!/usr/bin/env bash
# Restore Desiderium PostgreSQL from a gzipped pg_dump backup.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup.sql.gz> [--yes]" >&2
  echo "  Restores into the database configured via DATABASE_URL or PG* env vars." >&2
  exit 1
fi

BACKUP_FILE="$1"
CONFIRM="${2:-}"

if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "Backup file not found: ${BACKUP_FILE}" >&2
  exit 1
fi

if [[ "${CONFIRM}" != "--yes" ]]; then
  echo "WARNING: This will DROP and recreate public schema objects in the target database."
  echo "Re-run with --yes to proceed: $0 ${BACKUP_FILE} --yes"
  exit 2
fi

echo "[restore] applying ${BACKUP_FILE}"

if [[ -n "${DATABASE_URL:-}" ]]; then
  PGURL="${DATABASE_URL/postgresql+asyncpg/postgresql}"
  gunzip -c "${BACKUP_FILE}" | psql "${PGURL}" -v ON_ERROR_STOP=1
else
  : "${PGHOST:?PGHOST or DATABASE_URL required}"
  : "${PGUSER:?PGUSER required}"
  : "${PGDATABASE:?PGDATABASE required}"
  gunzip -c "${BACKUP_FILE}" | psql -v ON_ERROR_STOP=1
fi

echo "[restore] completed"
