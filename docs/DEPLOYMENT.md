# Deployment Guide — SENTINEL X

## A. Local development (recommended for FYP demos)

1. Start **Docker Desktop**.
2. From `D:\CyberSecurity_FYP` run `start.bat`.
3. Open http://127.0.0.1:5173 and login.
4. Stop with `stop.bat` (keeps Postgres volume on D:).

Health helper: `scripts\healthcheck.bat`  
Backup helper: `scripts\backup_data.bat`  
E2E tests: `scripts\run_e2e_tests.bat`

### Persistent storage (D:)

| Path | Contents |
|------|----------|
| `data/database/postgres` | PostgreSQL Docker volume |
| `data/pcaps` | Uploaded/demo captures |
| `data/secrets` | Encrypted OpenAI secret + Fernet key |
| `data/backups` | Manual backups |
| `ml/datasets` | Training CSVs |
| `ml/saved_models` | Joblib model artifacts |
| `logs` | Application logs (if configured) |
| `reports` | Generated report exports |

Restarting the app does **not** wipe these directories.

## B. Production-style deployment (same machine / isolated lab server)

This project is an **academic prototype**. Do not expose the simulated attack lab to the public internet.

### Components placement

| Component | Where it should run |
|-----------|---------------------|
| Attack VMs / GNS3 lab (optional) | Isolated lab network only |
| PCAP processing / Zeek | App server or monitoring host with lab capture access |
| FastAPI + ML + Agents | Application server (this project) |
| PostgreSQL | Local Docker on D: or dedicated DB host |
| React UI | Built static files behind reverse proxy |

### Steps

1. Copy `.env.production.example` → `.env` and set strong `SECRET_KEY` / DB passwords.
2. Change bootstrap admin passwords immediately after first login.
3. Start Postgres: `docker-compose up -d`
4. API (no reload): `scripts\start_backend_prod.bat`
5. Build UI: `scripts\build_frontend.bat` → serve `frontend\dist` with Nginx/Caddy.
6. Put TLS termination on the reverse proxy (HTTPS). Keep API bound to localhost and proxy `/api` + `/health`.

### Example Nginx sketch

```nginx
server {
  listen 443 ssl;
  server_name your-hostname.example;
  # ssl_certificate ...;
  # ssl_certificate_key ...;

  location /api/ {
    proxy_pass http://127.0.0.1:8000/api/;
  }
  location /health {
    proxy_pass http://127.0.0.1:8000/health;
  }
  location / {
    root D:/CyberSecurity_FYP/frontend/dist;
    try_files $uri /index.html;
  }
}
```

### Backups

Run `scripts\backup_data.bat` regularly. It dumps Postgres (if container is up) and copies secret store + model metrics.

### What not to do

- Do not publish OpenAI keys, DB passwords, or `.env` to Git.
- Do not expose Kali/GNS3 attack interfaces publicly.
- Do not enable unrestricted automatic blocking against non-lab IPs (guardrails reject public IPs).
