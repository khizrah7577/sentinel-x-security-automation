# Troubleshooting

## Backend will not start

- Confirm venv: `D:\CyberSecurity_FYP\.venv\Scripts\python.exe`
- Run `scripts\setup_venv.bat` if missing
- Ensure port 8000 free (`stop.bat` or close old Backend window)
- Check Docker Postgres: `docker ps` should show `cybersecurity_fyp_db`

## Database unavailable / health degraded

1. Start Docker Desktop  
2. `cd /d D:\CyberSecurity_FYP` → `docker-compose up -d`  
3. Wait until healthy, then restart backend  

Data directory: `D:\CyberSecurity_FYP\data\database\postgres`

## Frontend blank / API errors

- Confirm backend http://127.0.0.1:8000/health  
- Vite proxies `/api` and `/health` to the backend  
- Hard refresh browser; re-login if JWT expired  

## npm / node issues

- Node is on `D:\node` — `start.bat` prefers `D:\node\npm.cmd`  
- Reinstall deps: `cd frontend && npm install` with cache on D: if needed  

## PCAP upload rejected

- Only `.pcap` / `.pcapng` / `.cap`  
- Max 50 MB  
- Must have valid capture magic bytes  

## ML training fails

- Ensure baseline dataset: Datasets → Ensure synthetic baseline  
- CSV imports need a `label`/`Label` column  
- Artifacts write to `ml\saved_models` on D:  

## AI investigation says not configured

Expected without a key. Open **Settings → AI Configuration**.  
Rule-based investigation still works.

## OpenAI test connection fails

- Invalid/expired key  
- Network/DNS blocked to OpenAI  
- Key is removed/saved only on backend; frontend never receives the full key after save  

## Response action fails

- Only admins can approve/execute  
- Public IPs cannot be blocked  
- Mode `manual` approves without auto-execute — use Execute button  

## Disk space (C: almost full)

- Keep using D: project paths  
- Pip/npm caches under `data\cache`  
- Avoid downloading CICIDS/GNS3 until needed  

## Docker stack issues

- Start Docker Desktop first, then `start.bat`
- App URL is **http://127.0.0.1:8080** (not 5173)
- `docker compose logs backend` or `logs.bat backend`
- Port 8000 conflict: stop old `start-dev.bat` uvicorn, or change `BACKEND_HOST_PORT` in `.env`
- Postgres data is on `D:\CyberSecurity_FYP\data\database\postgres` — never use `docker compose down -v` unless you intend to wipe
- Frontend build fails: check `frontend` TypeScript with `npm run lint`
- Cloud ARM64: build on Ampere natively or use `scripts\build_multiarch.ps1 -Registry ... -Push`

