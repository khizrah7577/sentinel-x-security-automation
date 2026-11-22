# SENTINEL X — Deployment Readiness Report

Generated from live inspection (Windows 11 host + codebase).

## Host

| Item | Value |
|------|--------|
| OS | Windows 11 Pro (10.0.26300), AMD64 |
| RAM | ~16 GB host; Docker ~7.6 GB |
| C: | ~11 GB free (**low**) |
| D: | ~52 GB free — project + data target |
| Docker Desktop | 4.97 / Engine 29.9.2 |
| Compose | v5.6.1 |
| buildx | amd64 + arm64 capable |
| OCI credentials | **None** |

## Architecture (verified in Docker)

| Layer | Implementation |
|-------|----------------|
| Frontend | React/Vite SPA served by nginx container |
| Backend | FastAPI + ML inference + LangGraph + APScheduler in one process |
| DB | PostgreSQL 16 (D: bind mount locally) |
| Redis | Not used |
| Nginx | Reverse proxy, WS, rate limit, security headers |
| OpenAI | Runtime Settings UI / encrypted store only |
| Lab/Zeek | Local only — excluded from compose |

## Readiness verdict

| Goal | Status |
|------|--------|
| Local Docker deploy | **Ready and running** |
| Free cloud deploy files | **Ready** |
| Live OCI hosting | **Blocked** — need VM + SSH details |
| Move Docker Desktop disk to D: | **Awaiting your approval** |
