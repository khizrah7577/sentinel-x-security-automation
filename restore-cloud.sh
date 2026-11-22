#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
BDIR="${1:-}"
if [[ -z "$BDIR" || ! -f "${BDIR}/db.sql" ]]; then
  echo "Usage: $0 /path/to/backup_dir"
  echo "Refusing to run without an explicit backup path."
  exit 1
fi
read -r -p "Type YES to overwrite production database: " CONFIRM
[[ "$CONFIRM" == "YES" ]] || { echo "Cancelled."; exit 0; }
set -a; source .env.cloud; set +a
cat "${BDIR}/db.sql" | docker compose -f docker-compose.prod.yml --env-file .env.cloud exec -T postgres \
  psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB:-sentinel_x}"
echo "Restore complete."
