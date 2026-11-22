#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="${ROOT}/data/backups/${STAMP}"
mkdir -p "$OUT"
# shellcheck disable=SC1091
set -a; source .env.cloud; set +a
docker compose -f docker-compose.prod.yml --env-file .env.cloud exec -T postgres \
  pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB:-sentinel_x}" > "${OUT}/db.sql"
docker run --rm -v sentinel_x_prod_app_models:/src -v "${OUT}:/dst" alpine \
  sh -c 'cp -a /src/. /dst/ml/ 2>/dev/null || mkdir -p /dst/ml'
echo "Backup: ${OUT}"
