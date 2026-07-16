#!/usr/bin/env bash
# Report disk usage and exit non-zero when above threshold.
set -euo pipefail

PATH_TO_CHECK="${1:-/}"
WARN_PERCENT="${DISK_WARN_PERCENT:-85}"

read -r total used avail pct mount <<<"$(df -P "${PATH_TO_CHECK}" | awk 'NR==2 {print $2, $3, $4, $5, $6}')"
pct_num="${pct%%%}"

echo "disk path=${PATH_TO_CHECK} used=${used}KB total=${total}KB free=${avail}KB used_percent=${pct_num}"

if [[ "${pct_num}" -ge "${WARN_PERCENT}" ]]; then
  echo "WARN: disk usage ${pct_num}% >= threshold ${WARN_PERCENT}%" >&2
  exit 1
fi
