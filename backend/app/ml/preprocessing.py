"""Dataset loading and preprocessing with leakage-safe train/test split."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from app.ml.features import FEATURE_COLUMNS, LABEL_COLUMN


class DatasetPrepError(ValueError):
    pass


def load_csv_dataset(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise DatasetPrepError(f"Dataset not found: {path}")
    df = pd.read_csv(path)
    if df.empty:
        raise DatasetPrepError("Dataset is empty")
    return df


def normalize_label_series(series: pd.Series) -> pd.Series:
    mapping = {
        "normal": 0,
        "benign": 0,
        "0": 0,
        0: 0,
        "attack": 1,
        "suspicious": 1,
        "malicious": 1,
        "dos": 1,
        "ddos": 1,
        "brute force": 1,
        "bruteforce": 1,
        "portscan": 1,
        "port scanning": 1,
        "1": 1,
        1: 1,
    }

    def map_one(v: Any) -> int:
        if isinstance(v, (int, np.integer)):
            return 1 if int(v) != 0 else 0
        key = str(v).strip().lower()
        if key in mapping:
            return int(mapping[key])
        # CICIDS-style: anything not BENIGN treated as attack when column is Label
        if key == "benign":
            return 0
        return 1

    return series.map(map_one).astype(int)


def prepare_supervised_frame(df: pd.DataFrame, label_col: str | None = None) -> pd.DataFrame:
    cols_lower = {c.lower().strip(): c for c in df.columns}
    if label_col is None:
        for candidate in ("label", " Label", "Label", "attack", "class"):
            if candidate in df.columns:
                label_col = candidate
                break
            if candidate.lower().strip() in cols_lower:
                label_col = cols_lower[candidate.lower().strip()]
                break
    if label_col is None or label_col not in df.columns:
        raise DatasetPrepError("No label column found (expected 'label' or 'Label').")

    # If frame already matches FEATURE_COLUMNS, use directly
    if set(FEATURE_COLUMNS).issubset(set(df.columns)):
        out = df[FEATURE_COLUMNS].copy()
        out[LABEL_COLUMN] = normalize_label_series(df[label_col])
    else:
        # Best-effort mapping for compatible flow CSVs
        rename_map = {}
        aliases = {
            "source_port": ["source_port", "src_port", "sport", "Source Port"],
            "dest_port": ["dest_port", "dst_port", "dport", "Destination Port"],
            "duration": ["duration", "Flow Duration", "flow_duration"],
            "packet_count": ["packet_count", "total_packets", "Total Fwd Packets", "packets"],
            "bytes_transferred": ["bytes_transferred", "total_bytes", "Total Length of Fwd Packets", "bytes"],
        }
        work = pd.DataFrame()
        for dest, options in aliases.items():
            found = None
            for opt in options:
                if opt in df.columns:
                    found = opt
                    break
                if opt.lower() in cols_lower:
                    found = cols_lower[opt.lower()]
                    break
            if found is None:
                work[dest] = 0.0
            else:
                work[dest] = pd.to_numeric(df[found], errors="coerce").fillna(0.0)
        for col in FEATURE_COLUMNS:
            if col not in work.columns:
                work[col] = 0.0
        work = work[FEATURE_COLUMNS]
        work[LABEL_COLUMN] = normalize_label_series(df[label_col])
        out = work

    out = out.replace([np.inf, -np.inf], np.nan)
    missing = int(out.isna().sum().sum())
    out = out.fillna(0.0)
    before = len(out)
    out = out.drop_duplicates()
    duplicates = before - len(out)
    out.attrs["missing_values"] = missing
    out.attrs["duplicate_records"] = duplicates
    out.attrs["label_distribution"] = out[LABEL_COLUMN].value_counts().to_dict()
    return out


def split_xy(
    df: pd.DataFrame,
    test_size: float = 0.25,
    random_state: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, StandardScaler]:
    if LABEL_COLUMN not in df.columns:
        raise DatasetPrepError("Prepared frame missing label column")
    x = df[FEATURE_COLUMNS].to_numpy(dtype=float)
    y = df[LABEL_COLUMN].to_numpy(dtype=int)
    if len(np.unique(y)) < 2:
        raise DatasetPrepError("Dataset must contain both normal and attack labels for supervised training")

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )
    scaler = StandardScaler()
    x_train_s = scaler.fit_transform(x_train)
    x_test_s = scaler.transform(x_test)
    return x_train_s, x_test_s, y_train, y_test, scaler


def dataset_profile(df: pd.DataFrame) -> dict[str, Any]:
    labels = df[LABEL_COLUMN].value_counts().to_dict() if LABEL_COLUMN in df.columns else {}
    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "missing_values": int(df.attrs.get("missing_values", df.isna().sum().sum())),
        "duplicate_records": int(df.attrs.get("duplicate_records", 0)),
        "label_distribution": {str(k): int(v) for k, v in labels.items()},
        "feature_columns": FEATURE_COLUMNS,
    }


def write_profile(path: Path, profile: dict[str, Any]) -> None:
    path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
