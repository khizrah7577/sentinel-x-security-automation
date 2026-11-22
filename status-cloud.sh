#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
docker compose -f docker-compose.prod.yml --env-file .env.cloud ps
echo "---"
curl -fsS http://127.0.0.1/health || echo "health DOWN"
df -h /
free -h
