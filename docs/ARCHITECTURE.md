# Architecture

## High-level layers

1. **Simulated / offline network input** — PCAP upload, labelled demo capture (GNS3 optional)
2. **Monitoring & feature extraction** — Scapy primary; Zeek optional offline runner
3. **ML detection** — Random Forest, SVM, Isolation Forest (shared feature schema)
4. **Agentic investigation** — LangGraph: Monitoring → Investigation → Decision → Response prep → Explanation
5. **Response management** — Allowlisted actions, approval modes, simulated lab firewall, audit
6. **Presentation** — React SOC dashboard (light/dark), FastAPI REST API, PostgreSQL

## Request flow (primary demo path)

```
PCAP upload → validate/store on D: → Scapy flows → DB traffic/events
    → ML predict → predictions table
    → LangGraph investigation → incident + recommendation
    → Admin approve → allowlisted execute → verify/rollback → dashboard/report
```

## Key design rules

- ML labels come from sklearn models, not the LLM.
- Agents may only reason over an **evidence pack** of confirmed fields.
- OpenAI key is optional and stored encrypted under `data/secrets` via Settings UI.
- Response actions are allowlisted; no arbitrary shell from LLM output.
- Lab IP validation blocks public address enforcement in this prototype.

## Tech stack

- Backend: FastAPI, SQLAlchemy, Pydantic, LangGraph, scikit-learn, Scapy
- Frontend: React, TypeScript, Vite, Tailwind, Recharts
- DB: PostgreSQL 16 (Docker), volume on `D:\CyberSecurity_FYP\data\database\postgres`
