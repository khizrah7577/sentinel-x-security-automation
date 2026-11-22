# Security Guide

## Defaults to change

- `SECRET_KEY`
- Postgres password
- Bootstrap admin/analyst passwords
- Prefer HTTPS + domain in cloud

## Built-in controls

- Passwords hashed (bcrypt)
- JWT auth + admin/analyst roles
- CORS allow-list via `FRONTEND_ORIGIN` / `CORS_ORIGINS`
- OpenAI key stored encrypted in `data/secrets` (backend only)
- Response actions allowlisted; disruptive = approval required
- Nginx rate limit on `/api/`
- Security headers (frame, content-type, referrer, permissions)
- Cloud compose does not publish Postgres

## Never expose

- Database ports publicly
- Docker API
- Attack lab / Kali / Zeek UI
- Raw OpenAI keys in frontend, git, or logs

## Uploads

- PCAPs stored as files under `data/pcaps` (not inside Postgres)
- Metadata only in DB
- Cloud upload size limited by nginx `client_max_body_size`
