# Offline PCAP Pipeline (Phase 5)

## Modes

| Mode | Description |
|------|-------------|
| **offline** (default) | Upload PCAP / create demo capture; process with Scapy |
| **zeek** (optional) | If Zeek binary is installed and enabled, offline `zeek -r` is attempted first; Scapy still extracts features |

Live GNS3 capture is **not** required for demos.

## API

- `POST /api/v1/network/pcaps/upload`
- `POST /api/v1/network/pcaps/demo`
- `POST /api/v1/network/pcaps/{id}/process`
- `GET /api/v1/network/pcaps/{id}/traffic`
- `GET /api/v1/network/stats`

## Storage

- Files: `D:\CyberSecurity_FYP\data\pcaps`
- Processed Zeek logs (if any): `D:\CyberSecurity_FYP\data\processed\pcap_{id}\zeek`
- Metadata + flows: PostgreSQL

## Demo capture

`demo_offline_mixed_traffic.pcap` is explicitly marked `is_demo=true` and contains:

- Normal DNS + HTTP handshake
- Repeated SSH SYNs
- High-rate HTTP SYN burst

Heuristic labels are rule-based hints, not ML (ML arrives in Phase 6).
