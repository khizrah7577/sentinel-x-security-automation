"""Flow-level feature extraction from PCAP using Scapy (Zeek-independent fallback)."""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class FlowFeatures:
    source_ip: str
    dest_ip: str
    source_port: int
    dest_port: int
    protocol: str
    duration: float
    packet_count: int
    bytes_transferred: int
    connection_state: str
    tcp_flags: str
    syn_count: int = 0
    rst_count: int = 0
    fin_count: int = 0
    unique_dst_ports: int = 0
    raw_features: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        raw = data.pop("raw_features") or {}
        data["raw_features_json"] = json.dumps({**raw, **{k: data[k] for k in ("syn_count", "rst_count", "fin_count", "unique_dst_ports")}})
        return data


def _proto_name(pkt) -> str:
    if pkt.haslayer("TCP"):
        return "TCP"
    if pkt.haslayer("UDP"):
        return "UDP"
    if pkt.haslayer("ICMP"):
        return "ICMP"
    return "OTHER"


def _tcp_flag_str(pkt) -> str:
    if not pkt.haslayer("TCP"):
        return ""
    flags = pkt["TCP"].flags
    # Scapy FlagValue supports string conversion
    return str(flags)


def extract_flows_from_pcap(pcap_path: Path, max_packets: int = 20000) -> list[FlowFeatures]:
    """Aggregate packets into bidirectional-ish 5-tuple flows."""
    try:
        from scapy.all import IP, IPv6, rdpcap  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Scapy is required for PCAP feature extraction: {exc}") from exc

    path = Path(pcap_path)
    if not path.exists():
        raise FileNotFoundError(str(path))

    packets = rdpcap(str(path), count=max_packets)
    buckets: dict[tuple, dict[str, Any]] = defaultdict(
        lambda: {
            "packet_count": 0,
            "bytes": 0,
            "first_ts": None,
            "last_ts": None,
            "flags": set(),
            "syn": 0,
            "rst": 0,
            "fin": 0,
            "dst_ports": set(),
        }
    )

    for pkt in packets:
        ts = float(getattr(pkt, "time", 0.0) or 0.0)
        ip_layer = pkt.getlayer(IP) or pkt.getlayer(IPv6)
        if ip_layer is None:
            continue

        src = getattr(ip_layer, "src", "")
        dst = getattr(ip_layer, "dst", "")
        proto = _proto_name(pkt)
        sport = 0
        dport = 0
        if pkt.haslayer("TCP"):
            sport = int(pkt["TCP"].sport)
            dport = int(pkt["TCP"].dport)
        elif pkt.haslayer("UDP"):
            sport = int(pkt["UDP"].sport)
            dport = int(pkt["UDP"].dport)

        key = (src, dst, sport, dport, proto)
        b = buckets[key]
        b["packet_count"] += 1
        b["bytes"] += len(pkt)
        b["first_ts"] = ts if b["first_ts"] is None else min(b["first_ts"], ts)
        b["last_ts"] = ts if b["last_ts"] is None else max(b["last_ts"], ts)
        b["dst_ports"].add(dport)
        flag = _tcp_flag_str(pkt)
        if flag:
            b["flags"].add(flag)
            if "S" in flag and "A" not in flag:
                b["syn"] += 1
            if "R" in flag:
                b["rst"] += 1
            if "F" in flag:
                b["fin"] += 1

    flows: list[FlowFeatures] = []
    for (src, dst, sport, dport, proto), b in buckets.items():
        duration = 0.0
        if b["first_ts"] is not None and b["last_ts"] is not None:
            duration = max(0.0, float(b["last_ts"]) - float(b["first_ts"]))
        state = "unknown"
        if b["rst"]:
            state = "RST"
        elif b["fin"]:
            state = "FIN"
        elif b["syn"] and not b["fin"]:
            state = "SYN"
        elif proto == "UDP":
            state = "UDP"
        flows.append(
            FlowFeatures(
                source_ip=str(src),
                dest_ip=str(dst),
                source_port=int(sport),
                dest_port=int(dport),
                protocol=proto,
                duration=duration,
                packet_count=int(b["packet_count"]),
                bytes_transferred=int(b["bytes"]),
                connection_state=state,
                tcp_flags=",".join(sorted(b["flags"]))[:64],
                syn_count=int(b["syn"]),
                rst_count=int(b["rst"]),
                fin_count=int(b["fin"]),
                unique_dst_ports=len(b["dst_ports"]),
                raw_features={
                    "extractor": "scapy",
                    "max_packets_cap": max_packets,
                },
            )
        )

    logger.info("Extracted %s flows from %s (%s packets read)", len(flows), path.name, len(packets))
    return flows


def heuristic_suspicious(flow: FlowFeatures) -> tuple[bool, str]:
    """Lightweight per-flow rule hints used before ML (Phase 6). Not a substitute for ML."""
    reasons: list[str] = []
    if flow.protocol == "TCP" and flow.syn_count >= 3 and flow.packet_count <= 5:
        reasons.append("Repeated SYN attempts with few packets")
    if flow.dest_port in {22, 23, 3389} and flow.syn_count >= 5:
        reasons.append("Multiple connection attempts to remote admin port")
    if flow.protocol == "TCP" and flow.rst_count >= 3:
        reasons.append("Repeated RST responses")
    if flow.packet_count >= 200 and flow.duration < 2.0:
        reasons.append("High packet rate in short duration (possible flood)")
    # Single-packet SYN to admin ports is weak alone — aggregate pass may escalate.
    if flow.protocol == "TCP" and flow.syn_count >= 1 and flow.packet_count <= 2 and flow.dest_port in {22, 23, 3389}:
        reasons.append("SYN probe toward remote admin service")
    return (len(reasons) > 0, "; ".join(reasons))


def apply_aggregate_heuristics(flows: list[FlowFeatures]) -> dict[int, str]:
    """
    Mark flows suspicious based on source behavior across the capture.
    Returns map of flow index -> extra reason string.
    """
    extras: dict[int, str] = {}
    by_src_admin: dict[str, list[int]] = defaultdict(list)
    by_src_http_syn: dict[str, list[int]] = defaultdict(list)

    for idx, flow in enumerate(flows):
        if flow.protocol == "TCP" and flow.dest_port in {22, 23, 3389} and flow.syn_count >= 1:
            by_src_admin[flow.source_ip].append(idx)
        if flow.protocol == "TCP" and flow.dest_port == 80 and flow.syn_count >= 1 and flow.packet_count <= 2:
            by_src_http_syn[flow.source_ip].append(idx)

    for src, idxs in by_src_admin.items():
        if len(idxs) >= 5:
            for i in idxs:
                extras[i] = f"Repeated SSH/admin connection attempts from {src}"
    for src, idxs in by_src_http_syn.items():
        if len(idxs) >= 20:
            for i in idxs:
                extras[i] = f"High-rate SYN burst to HTTP from {src} (possible DoS demo pattern)"
    return extras
