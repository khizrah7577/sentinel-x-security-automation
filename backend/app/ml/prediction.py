"""Run predictions with a saved artifact."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from app.ml.features import FEATURE_COLUMNS, traffic_record_to_row
from app.ml.training import load_artifact


def severity_from_confidence(label: int, confidence: float) -> str:
    if label == 0:
        return "informational"
    if confidence >= 0.9:
        return "critical"
    if confidence >= 0.75:
        return "high"
    if confidence >= 0.6:
        return "medium"
    return "low"


def predict_rows(artifact: dict[str, Any], feature_rows: list[dict[str, float]]) -> list[dict[str, Any]]:
    model = artifact["model"]
    scaler = artifact["scaler"]
    cols = artifact.get("feature_columns") or FEATURE_COLUMNS
    matrix = np.asarray([[row.get(c, 0.0) for c in cols] for row in feature_rows], dtype=float)
    matrix_s = scaler.transform(matrix)

    model_type = artifact.get("metrics", {}).get("model_type", "")
    if model_type == "isolation_forest" or model.__class__.__name__ == "IsolationForest":
        raw = model.predict(matrix_s)
        labels = np.where(raw == -1, 1, 0)
        # decision_function: lower = more anomalous
        scores = model.decision_function(matrix_s)
        # map to 0..1 confidence for attack
        confidences = 1 / (1 + np.exp(scores))
        anomaly_scores = scores
    else:
        labels = model.predict(matrix_s)
        anomaly_scores = [None] * len(labels)
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(matrix_s)
            # probability of class 1 if present
            classes = list(getattr(model, "classes_", [0, 1]))
            if 1 in classes:
                idx = classes.index(1)
                confidences = proba[:, idx]
            else:
                confidences = np.max(proba, axis=1)
        else:
            confidences = np.ones(len(labels)) * 0.5

    results = []
    for i, label in enumerate(labels):
        lab = int(label)
        conf = float(confidences[i])
        results.append(
            {
                "predicted_label": "attack" if lab == 1 else "normal",
                "attack_category": "suspicious_or_attack" if lab == 1 else "normal",
                "confidence": conf if lab == 1 else float(1.0 - conf),
                "anomaly_score": None if anomaly_scores[i] is None else float(anomaly_scores[i]),
                "severity": severity_from_confidence(lab, conf if lab == 1 else 1.0 - conf),
            }
        )
    return results


def predict_traffic_records(artifact_path: Path, records: list[Any]) -> list[dict[str, Any]]:
    artifact = load_artifact(artifact_path)
    rows = [traffic_record_to_row(r) for r in records]
    return predict_rows(artifact, rows)
