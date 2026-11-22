"""Train Random Forest, SVM, and Isolation Forest with real metrics."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV

from app.ml.features import FEATURE_COLUMNS


def _binary_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = (int(x) for x in cm.ravel()) if cm.size == 4 else (0, 0, 0, 0)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
        "false_positives": fp,
        "false_negatives": fn,
        "true_positives": tp,
        "true_negatives": tn,
        "confusion_matrix": cm.tolist(),
        "classification_report": classification_report(
            y_true, y_pred, target_names=["normal", "attack"], zero_division=0
        ),
    }


def train_random_forest(x_train, y_train, x_test, y_test) -> tuple[Any, dict[str, Any], float]:
    t0 = time.perf_counter()
    model = RandomForestClassifier(
        n_estimators=120,
        max_depth=12,
        random_state=42,
        class_weight="balanced_subsample",
        n_jobs=-1,
    )
    model.fit(x_train, y_train)
    duration = time.perf_counter() - t0
    pred = model.predict(x_test)
    metrics = _binary_metrics(y_test, pred)
    metrics["model_type"] = "random_forest"
    metrics["duration_seconds"] = duration
    return model, metrics, duration


def train_svm(x_train, y_train, x_test, y_test) -> tuple[Any, dict[str, Any], float]:
    t0 = time.perf_counter()
    base = LinearSVC(class_weight="balanced", random_state=42, max_iter=5000)
    # probability-like scores via calibration for confidence
    model = CalibratedClassifierCV(base, cv=3)
    model.fit(x_train, y_train)
    duration = time.perf_counter() - t0
    pred = model.predict(x_test)
    metrics = _binary_metrics(y_test, pred)
    metrics["model_type"] = "svm"
    metrics["duration_seconds"] = duration
    return model, metrics, duration


def train_isolation_forest(x_train, y_train, x_test, y_test) -> tuple[Any, dict[str, Any], float]:
    """Unsupervised anomaly model; evaluated by mapping anomalies -> attack label."""
    t0 = time.perf_counter()
    # Fit mostly on normal class when available to reduce trivial collapse
    normal_mask = y_train == 0
    fit_x = x_train[normal_mask] if normal_mask.any() else x_train
    contamination = float(np.clip((y_train == 1).mean(), 0.05, 0.4))
    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(fit_x)
    duration = time.perf_counter() - t0
    raw = model.predict(x_test)  # 1 normal, -1 anomaly
    pred = np.where(raw == -1, 1, 0)
    metrics = _binary_metrics(y_test, pred)
    metrics["model_type"] = "isolation_forest"
    metrics["duration_seconds"] = duration
    metrics["contamination"] = contamination
    return model, metrics, duration


def save_artifact(
    model_dir: Path,
    *,
    name: str,
    model: Any,
    scaler: Any,
    metrics: dict[str, Any],
) -> Path:
    model_dir.mkdir(parents=True, exist_ok=True)
    path = model_dir / f"{name}.joblib"
    payload = {
        "model": model,
        "scaler": scaler,
        "feature_columns": FEATURE_COLUMNS,
        "metrics": metrics,
    }
    joblib.dump(payload, path)
    (model_dir / f"{name}_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return path


def load_artifact(path: Path) -> dict[str, Any]:
    return joblib.load(path)
