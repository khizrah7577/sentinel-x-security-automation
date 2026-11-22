"""Generate a labelled synthetic flow dataset for local training (not CICIDS)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app.ml.features import FEATURE_COLUMNS, LABEL_COLUMN, dataframe_from_rows, flow_to_feature_row


def generate_synthetic_flow_dataset(
    output_path: Path,
    n_normal: int = 800,
    n_attack: int = 800,
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, float]] = []
    labels: list[int] = []

    # Normal browsing / DNS / SSH success-ish
    for _ in range(n_normal):
        kind = rng.choice(["http", "dns", "ssh_ok"])
        if kind == "http":
            row = flow_to_feature_row(
                source_port=int(rng.integers(49152, 65535)),
                dest_port=80 if rng.random() < 0.7 else 443,
                duration=float(rng.uniform(0.05, 8.0)),
                packet_count=int(rng.integers(4, 80)),
                bytes_transferred=int(rng.integers(400, 40000)),
                protocol="TCP",
                raw_features_json='{"syn_count":1,"rst_count":0,"fin_count":1,"unique_dst_ports":1}',
            )
        elif kind == "dns":
            row = flow_to_feature_row(
                source_port=int(rng.integers(49152, 65535)),
                dest_port=53,
                duration=float(rng.uniform(0.001, 0.2)),
                packet_count=int(rng.integers(1, 4)),
                bytes_transferred=int(rng.integers(60, 400)),
                protocol="UDP",
                raw_features_json='{"syn_count":0,"rst_count":0,"fin_count":0,"unique_dst_ports":1}',
            )
        else:
            row = flow_to_feature_row(
                source_port=int(rng.integers(49152, 65535)),
                dest_port=22,
                duration=float(rng.uniform(1.0, 30.0)),
                packet_count=int(rng.integers(10, 120)),
                bytes_transferred=int(rng.integers(800, 20000)),
                protocol="TCP",
                raw_features_json='{"syn_count":1,"rst_count":0,"fin_count":1,"unique_dst_ports":1}',
            )
        rows.append(row)
        labels.append(0)

    # Attack-like: brute, scan, flood
    for _ in range(n_attack):
        kind = rng.choice(["ssh_brute", "port_scan", "syn_flood"])
        if kind == "ssh_brute":
            row = flow_to_feature_row(
                source_port=int(rng.integers(40000, 50000)),
                dest_port=22,
                duration=float(rng.uniform(0.0, 0.5)),
                packet_count=int(rng.integers(1, 3)),
                bytes_transferred=int(rng.integers(40, 120)),
                protocol="TCP",
                raw_features_json='{"syn_count":1,"rst_count":1,"fin_count":0,"unique_dst_ports":1}',
            )
        elif kind == "port_scan":
            row = flow_to_feature_row(
                source_port=int(rng.integers(40000, 60000)),
                dest_port=int(rng.choice([21, 22, 23, 80, 443, 3389, 8080])),
                duration=float(rng.uniform(0.0, 0.05)),
                packet_count=1,
                bytes_transferred=int(rng.integers(40, 80)),
                protocol="TCP",
                raw_features_json='{"syn_count":1,"rst_count":0,"fin_count":0,"unique_dst_ports":1}',
            )
        else:
            row = flow_to_feature_row(
                source_port=int(rng.integers(20000, 30000)),
                dest_port=80,
                duration=float(rng.uniform(0.0, 0.2)),
                packet_count=int(rng.integers(1, 3)),
                bytes_transferred=int(rng.integers(40, 100)),
                protocol="TCP",
                raw_features_json='{"syn_count":1,"rst_count":0,"fin_count":0,"unique_dst_ports":1}',
            )
        rows.append(row)
        labels.append(1)

    df = dataframe_from_rows(rows, labels)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df


def ensure_default_dataset(dataset_dir: Path) -> Path:
    path = dataset_dir / "synthetic_flow_baseline.csv"
    if not path.exists():
        generate_synthetic_flow_dataset(path)
    return path
