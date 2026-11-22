#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
[[ -f .env.cloud ]] || { echo "Missing .env.cloud"; exit 1; }
docker compose -f docker-compose.prod.yml --env-file .env.cloud pull || true
docker compose -f docker-compose.prod.yml --env-file .env.cloud build --pull
docker compose -f docker-compose.prod.yml --env-file .env.cloud up -d --remove-orphans
docker compose -f docker-compose.prod.yml --env-file .env.cloud ps
