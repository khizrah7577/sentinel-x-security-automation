# Docker Architecture

```
Browser
  │
  ▼
nginx (:8080 local / :80 cloud)
  ├── /           → frontend (nginx alpine static SPA)
  ├── /api/       → backend :8000
  ├── /health     → backend
  └── /api/v1/automation/ws → backend WebSocket
        │
        ▼
   FastAPI backend
   ├── SQLAlchemy → postgres :5432 (internal name: postgres)
   ├── APScheduler (automation tasks in-process)
   ├── ML joblib models (volume)
   └── LangGraph agents (OpenAI optional via encrypted store)
```

## Why not separate worker containers?

APScheduler and ML inference already run inside the FastAPI process. Extra worker containers would waste Always Free RAM without benefit for this FYP size.

## Local vs prod compose

| | `docker-compose.yml` | `docker-compose.prod.yml` |
|--|----------------------|---------------------------|
| Postgres host port | 5432 published | **not published** |
| App port | 8080 | 80/443 |
| Volumes | D: bind mounts | named Docker volumes |
| Resources | none | CPU/memory limits |
| Lab services | none | none |

## Files

- `Dockerfile.backend`
- `Dockerfile.frontend`
- `docker/nginx/nginx.conf` / `nginx.prod.conf`
- `.dockerignore`
