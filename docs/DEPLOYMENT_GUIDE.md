# SENTINEL X — Deployment Guide

Easy overview of how to run SENTINEL X with Docker.

## Two environments

| Environment | How |
|-------------|-----|
| Local Windows | Docker Desktop + `start.bat` → http://127.0.0.1:8080 |
| Oracle Cloud Always Free | Ubuntu ARM64 + `deploy-cloud.sh` (after you create the VM) |

## What runs in Docker

1. **nginx** — public entry (UI + `/api` + WebSockets)
2. **frontend** — React static build
3. **backend** — FastAPI + ML inference + LangGraph agents + APScheduler automation
4. **postgres** — persistent database

No Redis. No Kali/Zeek/lab machines in the cloud stack.

## Local (Windows)

```bat
cd /d D:\CyberSecurity_FYP
start.bat
status.bat
```

- App: http://127.0.0.1:8080  
- API docs: http://127.0.0.1:8000/docs  
- Login: `admin@localhost` / `ChangeMeAdmin123!` (change after first login)

Old venv mode (no full Docker app): `start-dev.bat`

## Cloud (after OCI VM exists)

1. Create Always Free Ampere A1 Ubuntu ARM64 VM (manual in OCI console).
2. Copy project to the server.
3. Create `.env.cloud` from `.env.cloud.example`.
4. Run `./deploy-cloud.sh`.

**Cloud is not live until you provision a real server.** This laptop has no OCI credentials.

## OpenAI

Leave keys empty in env files. After login → **Settings → AI Configuration**.

## More detail

- `LOCAL_DOCKER_GUIDE.md`
- `ORACLE_CLOUD_GUIDE.md`
- `DOCKER_ARCHITECTURE.md`
- `SECURITY_GUIDE.md`
- `BACKUP_RESTORE_GUIDE.md`
- `TROUBLESHOOTING.md`
- `DEPLOYMENT_READINESS.md`
