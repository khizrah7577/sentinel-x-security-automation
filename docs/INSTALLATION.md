# Installation Guide — CyberSecurity_FYP

## Prerequisites (already verified on this machine)

- Python 3.12.10
- Node.js 26+ / npm
- Git
- Docker Desktop (optional for PostgreSQL; daemon must be running)

## Project location

All project files: `D:\CyberSecurity_FYP`

## Setup steps

1. Ensure Docker Desktop is started if you want PostgreSQL.
2. Create/refresh the venv (if needed):

```bat
D:\CyberSecurity_FYP\scripts\setup_venv.bat
```

3. Install frontend dependencies:

```bat
cd /d D:\CyberSecurity_FYP\frontend
set npm_config_cache=D:\CyberSecurity_FYP\data\cache\npm
npm install
```

4. Copy environment file if missing:

```bat
copy .env.example .env
```

5. Start services:

```bat
D:\CyberSecurity_FYP\start.bat
```

6. Stop database container:

```bat
D:\CyberSecurity_FYP\stop.bat
```

## Health checks

- Backend: http://127.0.0.1:8000/health
- API docs: http://127.0.0.1:8000/docs
- Frontend: http://127.0.0.1:5173
- Helper: `scripts\healthcheck.bat`

## Storage notes

- Pip cache: `D:\CyberSecurity_FYP\data\cache\pip`
- npm cache: `D:\CyberSecurity_FYP\data\cache\npm`
- Postgres volume: `D:\CyberSecurity_FYP\data\database\postgres`
- Secrets: `D:\CyberSecurity_FYP\data\secrets` (never commit)

## Related docs

- [Deployment](DEPLOYMENT.md) · [User Guide](USER_GUIDE.md) · [FYP Demo](FYP_DEMO_GUIDE.md)
- [Troubleshooting](TROUBLESHOOTING.md) · [Architecture](ARCHITECTURE.md)
- [Final QA](FINAL_QA_REPORT.md)
