# SENTINEL X

**Intelligent Cybersecurity & Threat Response Platform**

Academic Final Year Project prototype (Agentic AI cyber attack detection & automated response) for **controlled / offline** network environments.

**Project root:** `D:\CyberSecurity_FYP` (codebase path unchanged)

## Quick start (Docker)

```bat
cd /d D:\CyberSecurity_FYP
start.bat
```

| Service | URL |
|---------|-----|
| App (nginx) | http://127.0.0.1:8080 |
| API docs | http://127.0.0.1:8000/docs |
| Health | http://127.0.0.1:8080/health |

**Login:** `admin@localhost` / `ChangeMeAdmin123!`  
**Stop / status / logs / backup:** `stop.bat` `status.bat` `logs.bat` `backup.bat`  
**Dev without full Docker app:** `start-dev.bat` (Vite on :5173 + host uvicorn)

Oracle Cloud (Always Free ARM64): see [ORACLE_CLOUD_GUIDE](docs/ORACLE_CLOUD_GUIDE.md) — not live until you create a VM.

## What it does

1. Offline PCAP ingest + flow feature extraction (Scapy; Zeek optional)
2. ML detection — Random Forest, SVM, Isolation Forest
3. LangGraph multi-agent investigation (OpenAI key optional via Settings)
4. Allowlisted response actions with approval, verify, rollback
5. PostgreSQL persistence on D: + React SOC dashboard (light/dark)

## Documentation

| Doc | Purpose |
|-----|---------|
| [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) | Docker local + cloud overview |
| [Local Docker](docs/LOCAL_DOCKER_GUIDE.md) | Windows Docker Desktop |
| [Oracle Cloud](docs/ORACLE_CLOUD_GUIDE.md) | Always Free ARM64 |
| [Deployment Status](docs/DEPLOYMENT_STATUS.md) | What is live vs prepared |
| [Installation](docs/INSTALLATION.md) | Setup |
| [Deployment](docs/DEPLOYMENT.md) | Older local notes |
| [Architecture](docs/ARCHITECTURE.md) | System design |
| [Docker Architecture](docs/DOCKER_ARCHITECTURE.md) | Compose topology |
| [User Guide](docs/USER_GUIDE.md) | Operator usage |
| [FYP Demo Guide](docs/FYP_DEMO_GUIDE.md) | Examiner walkthrough |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common fixes |
| [Integration Test Report](docs/INTEGRATION_TEST_REPORT.md) | Verified E2E results |
| [Final QA Report](docs/FINAL_QA_REPORT.md) | Phase 11 acceptance sign-off |
| [Progress](docs/PROGRESS.md) | Phase tracker |
| [Project Structure](docs/PROJECT_STRUCTURE.md) | Folder map |

## Helper scripts

- `scripts\healthcheck.bat`
- `scripts\backup_data.bat`
- `scripts\run_e2e_tests.bat`
- `scripts\build_frontend.bat`
- `scripts\start_backend_prod.bat`

## Security notes

- Never commit `.env` or `data/secrets/`
- Configure OpenAI only via **Settings → AI Configuration**
- Agents cannot run arbitrary shell commands
- Lab IP guardrails reject public blocking targets
- Do not expose the attack lab to the public internet

## Stack

Python 3.12 · FastAPI · PostgreSQL · React/Vite/Tailwind · scikit-learn · LangGraph · Scapy
