"""Shared feature schema for training and inference (no leakage across stages)."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "source_port",
    "dest_port",
    "duration",
    "packet_count",
    "bytes_transferred",
    "protocol_tcp",
    "protocol_udp",
    "protocol_icmp",
    "syn_count",
    "rst_count",
    "fin_count",
    "unique_dst_ports",
    "admin_port",
    "syn_ratio",
    "bytes_per_packet",
]

LABEL_COLUMN = "label"  # 0=normal, 1=attack/suspicious
ADMIN_PORTS = {22, 23, 3389, 445, 21}


def _raw_dict(raw_features_json: str | None) -> dict[str, Any]:
    if not raw_features_json:
        return {}
    try:
        data = json.loads(raw_features_json)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def flow_to_feature_row(
    *,
    source_port: int,
    dest_port: int,
    duration: float,
    packet_count: int,
    bytes_transferred: int,
    protocol: str,
    raw_features_json: str = "",
) -> dict[str, float]:
    raw = _raw_dict(raw_features_json)
    proto = (protocol or "").upper()
    pkts = max(int(packet_count or 0), 0)
    syn = float(raw.get("syn_count", 0) or 0)
    rst = float(raw.get("rst_count", 0) or 0)
    fin = float(raw.get("fin_count", 0) or 0)
    uniq = float(raw.get("unique_dst_ports", 1) or 1)
    bpp = float(bytes_transferred or 0) / float(pkts) if pkts else 0.0
    return {
        "source_port": float(source_port or 0),
        "dest_port": float(dest_port or 0),
        "duration": float(duration or 0.0),
        "packet_count": float(pkts),
        "bytes_transferred": float(bytes_transferred or 0),
        "protocol_tcp": 1.0 if proto == "TCP" else 0.0,
        "protocol_udp": 1.0 if proto == "UDP" else 0.0,
        "protocol_icmp": 1.0 if proto == "ICMP" else 0.0,
        "syn_count": syn,
        "rst_count": rst,
        "fin_count": fin,
        "unique_dst_ports": uniq,
        "admin_port": 1.0 if int(dest_port or 0) in ADMIN_PORTS else 0.0,
        "syn_ratio": syn / float(pkts) if pkts else 0.0,
        "bytes_per_packet": bpp,
    }


def dataframe_from_rows(rows: list[dict[str, float]], labels: list[int] | None = None) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0
    df = df[FEATURE_COLUMNS].astype(float).fillna(0.0)
    if labels is not None:
        df[LABEL_COLUMN] = np.asarray(labels, dtype=int)
    return df


def traffic_record_to_row(record) -> dict[str, float]:
    return flow_to_feature_row(
        source_port=record.source_port,
        dest_port=record.dest_port,
        duration=record.duration,
        packet_count=record.packet_count,
        bytes_transferred=record.bytes_transferred,
        protocol=record.protocol,
        raw_features_json=record.raw_features_json or "",
    )
