# Phase 1 Environment Snapshot (2026-11-21)

## Disk

- C: ~12 GB free (critical)
- D: ~54 GB free (primary)

## Reused

- Python 3.12.10, Node.js on D:\node, Git on D:\Git, Docker Desktop (daemon often stopped), Cursor, VS Code, Ollama

## Deferred / missing

- Native PostgreSQL → Docker Compose Postgres with volume on D:
- Wireshark, Zeek, GNS3, VirtualBox
- CICIDS2017 dataset download

## Decision

Use Python 3.12 venv at `D:\CyberSecurity_FYP\.venv`, offline/PCAP-first monitoring, Docker Postgres when daemon is running.
