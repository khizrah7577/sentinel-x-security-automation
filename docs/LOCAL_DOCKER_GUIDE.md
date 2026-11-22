# Local Docker Guide (Windows 11)

## Prerequisites

- Docker Desktop running (WSL2 backend)
- Project on `D:\CyberSecurity_FYP`
- Prefer keeping large files on **D:** (C: is low on free space)

## First start

```bat
cd /d D:\CyberSecurity_FYP
copy .env.docker.example .env
start.bat
```

Scripts:

| Script | Action |
|--------|--------|
| `start.bat` | Build + start stack |
| `stop.bat` | Stop containers (keep data) |
| `restart.bat` | Stop then start |
| `status.bat` | Health + compose status |
| `logs.bat` | Follow logs (`logs.bat backend`) |
| `backup.bat` | Dump DB + models to `data\backups` |
| `restore.bat` | Restore (asks YES) |
| `update.bat` | Rebuild images |

## URLs

- UI + API via nginx: **http://127.0.0.1:8080**
- Backend direct: http://127.0.0.1:8000

## Data locations (D:)

| Data | Path |
|------|------|
| Postgres files | `D:\CyberSecurity_FYP\data\database\postgres` |
| PCAPs | `D:\CyberSecurity_FYP\data\pcaps` |
| Models | `D:\CyberSecurity_FYP\ml\saved_models` |
| Secrets (encrypted AI key) | `D:\CyberSecurity_FYP\data\secrets` |
| Logs / reports | `logs\`, `reports\` |

## Docker Desktop disk location

Docker Engine still stores images inside the Desktop VM (`/var/lib/docker`).  
**This project did not relocate Docker Desktop storage** (needs your approval — existing images/volumes could be affected).

Recommendation when you are ready: Docker Desktop → Settings → Resources → Advanced / Disk image location → folder on **D:**, then restart Desktop.

## Dev without full stack

```bat
start-dev.bat
```

Starts Postgres container + host Python/Node (previous workflow).
