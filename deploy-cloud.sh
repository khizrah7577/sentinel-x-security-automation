#!/usr/bin/env bash
# SENTINEL X — deploy on Ubuntu ARM64 (Oracle Always Free)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -f .env.cloud ]]; then
  echo "[ERROR] Missing .env.cloud — copy from .env.cloud.example and edit."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] Docker not installed. See docs/ORACLE_CLOUD_GUIDE.md"
  exit 1
fi

mkdir -p data/pcaps data/secrets data/uploads logs reports ml/saved_models ml/datasets

echo "[1/3] Building and starting production stack..."
docker compose -f docker-compose.prod.yml --env-file .env.cloud up -d --build

echo "[2/3] Waiting for health..."
sleep 8
docker compose -f docker-compose.prod.yml --env-file .env.cloud ps

echo "[3/3] Health check..."
curl -fsS "http://127.0.0.1:${HTTP_PORT:-80}/health" || curl -fsS http://127.0.0.1/health || true

echo
echo "Deploy attempted. Open FRONTEND_ORIGIN from .env.cloud in a browser."
echo "Configure OpenAI via Settings UI (never put keys in compose logs)."
