# SENTINEL X — Deployment Status (final)

Updated: 2026-11-22

## Local Docker — LIVE

| Check | Result |
|-------|--------|
| URL | **http://127.0.0.1:8080** |
| Containers | postgres, backend, frontend, nginx — **healthy** |
| Health | `ok`, DB connected |
| Login | PASS (`admin@localhost`) |
| Dashboard | 153 events, 147 attacks, 3 ML models |
| AI settings | `configured=false` (expected; set via UI) |
| Automation | 2/2 workflows, 6 scheduler tasks |
| Notifications | API OK |
| Reports | API OK |
| PCAP list | 3 uploads |
| WebSocket route | nginx proxies `/api/v1/automation/ws` |
| Backup | PASS — latest under `data\backups\` |
| Persistence | PASS after backend recreate (153 events) |
| Redis | Not required / not deployed |
| Attack lab / Zeek / Kali | Not in Docker stack (local-only) |

Scripts: `start.bat` `stop.bat` `restart.bat` `status.bat` `logs.bat` `backup.bat` `restore.bat` `update.bat`  
Dev fallback: `start-dev.bat` / `stop-dev.bat`

## Cloud (Oracle Always Free) — PREPARED, not live

| Item | Status |
|------|--------|
| OCI account / VM / SSH / IP | **Missing on this machine** |
| `docker-compose.prod.yml` | Ready (CPU/RAM limits, DB private, `CLOUD_LIGHTWEIGHT=true`) |
| Cloud scripts | `deploy-cloud.sh` + update/status/backup/restore |
| HTTPS helper | `scripts/setup_https_certbot.sh` |
| Checklist | `docs/oci-server-checklist.md` |
| Heavy ML training on cloud | **Blocked by API** when lightweight flags set |
| QEMU arm64 image build on Windows | Too slow for ML stack — **build natively on Ampere** |
| Base images arm64 | `python:3.12-slim-bookworm` publishes arm64 |

### What you must provide to go live on OCI

1. Always Free Ampere A1 Ubuntu ARM64 VM created  
2. Public IP  
3. SSH private key path + username  
4. Optional domain  

Until then, cloud deployment is **configured only**, not running online.

## Docker Desktop disk location

Still `/var/lib/docker` inside Desktop VM — **not moved to D:** (needs your approval).  
App data already uses D: bind mounts.

## Docs index

- `docs/DEPLOYMENT_GUIDE.md`
- `docs/LOCAL_DOCKER_GUIDE.md`
- `docs/ORACLE_CLOUD_GUIDE.md`
- `docs/DOCKER_ARCHITECTURE.md`
- `docs/SECURITY_GUIDE.md`
- `docs/BACKUP_RESTORE_GUIDE.md`
- `docs/TROUBLESHOOTING.md`
- `docs/DEPLOYMENT_READINESS.md`
- `docs/oci-server-checklist.md`
