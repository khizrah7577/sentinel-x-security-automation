# Network Lab Notes

## Current mode: Offline / PCAP-first

GNS3, VirtualBox/VMware, Wireshark, and Zeek were **not installed** during Phase 1/2 to protect C: disk space and avoid large downloads without approval.

The application supports:

- PCAP upload
- Offline replay / sample traffic
- Python feature extraction (Scapy) when Zeek is unavailable
- Clearly labelled demonstration events

## Optional later installs (requires approval)

| Component | Approx. size | Purpose |
|-----------|--------------|---------|
| Wireshark | ~0.5–1 GB | Packet capture / inspection |
| Zeek (Docker preferred) | ~1–2 GB image | Connection logs from PCAP |
| GNS3 + VMs | 20–40+ GB | Live simulated network |

Keep VM disks and capture files under `D:\CyberSecurity_FYP\` when installed.
