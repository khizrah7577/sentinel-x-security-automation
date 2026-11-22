"""ML dataset, training, activation, and prediction orchestration."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.ml.features import FEATURE_COLUMNS
from app.ml.preprocessing import (
    DatasetPrepError,
    dataset_profile,
    load_csv_dataset,
    prepare_supervised_frame,
    split_xy,
)
from app.ml.prediction import predict_traffic_records
from app.ml.synthetic_data import ensure_default_dataset
from app.ml.training import (
    save_artifact,
    train_isolation_forest,
    train_random_forest,
    train_svm,
)
from app.models.audit import AuditLog
from app.models.ml import (
    Dataset,
    DatasetStatus,
    MLModel,
    ModelType,
    Prediction,
    TrainingRun,
    TrainingStatus,
)
from app.models.network import NetworkEvent, TrafficLabel, TrafficRecord

logger = logging.getLogger(__name__)

TRAINERS = {
    ModelType.random_forest: train_random_forest,
    ModelType.svm: train_svm,
    ModelType.isolation_forest: train_isolation_forest,
}


def ensure_baseline_dataset(db: Session) -> Dataset:
    settings = get_settings()
    path = ensure_default_dataset(Path(settings.dataset_dir))
    existing = (
        db.query(Dataset)
        .filter(Dataset.stored_path == str(path))
        .first()
    )
    if existing:
        return existing

    raw = load_csv_dataset(path)
    prepared = prepare_supervised_frame(raw)
    profile = dataset_profile(prepared)
    ds = Dataset(
        name="Synthetic Flow Baseline",
        source="synthetic_local",
        stored_path=str(path),
        row_count=profile["row_count"],
        column_count=profile["column_count"],
        label_distribution_json=json.dumps(profile["label_distribution"]),
        missing_values=profile["missing_values"],
        duplicate_records=profile["duplicate_records"],
        status=DatasetStatus.ready,
        notes=(
            "Local synthetic labelled flows for offline training. "
            "Not CICIDS2017. Import CICIDS CSV later via dataset import when approved."
        ),
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return ds


def import_csv_dataset(
    db: Session,
    *,
    name: str,
    stored_path: Path,
    source: str = "csv_import",
    notes: str = "",
) -> Dataset:
    raw = load_csv_dataset(stored_path)
    prepared = prepare_supervised_frame(raw)
    profile = dataset_profile(prepared)
    # Persist a cleaned copy beside original
    clean_path = stored_path.with_name(stored_path.stem + "_prepared.csv")
    prepared.to_csv(clean_path, index=False)
    ds = Dataset(
        name=name,
        source=source,
        stored_path=str(clean_path),
        row_count=profile["row_count"],
        column_count=profile["column_count"],
        label_distribution_json=json.dumps(profile["label_distribution"]),
        missing_values=profile["missing_values"],
        duplicate_records=profile["duplicate_records"],
        status=DatasetStatus.ready,
        notes=notes or f"Imported from {stored_path.name}",
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return ds


def train_model(
    db: Session,
    *,
    model_type: ModelType,
    dataset_id: Optional[int],
    user_id: Optional[int],
    activate: bool = True,
) -> dict:
    if dataset_id is None:
        dataset = ensure_baseline_dataset(db)
    else:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise FileNotFoundError("Dataset not found")

    run = TrainingRun(
        dataset_id=dataset.id,
        model_type=model_type,
        status=TrainingStatus.running,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        path = Path(dataset.stored_path)
        raw = load_csv_dataset(path)
        prepared = prepare_supervised_frame(raw)
        x_train, x_test, y_train, y_test, scaler = split_xy(prepared)
        trainer = TRAINERS[model_type]
        model, metrics, duration = trainer(x_train, y_train, x_test, y_test)

        version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        name = f"{model_type.value}_{version}"
        artifact_path = save_artifact(
            Path(get_settings().model_dir),
            name=name,
            model=model,
            scaler=scaler,
            metrics=metrics,
        )

        if activate:
            db.query(MLModel).filter(MLModel.is_active.is_(True)).update({"is_active": False})

        ml_model = MLModel(
            name=name,
            model_type=model_type,
            version=version,
            stored_path=str(artifact_path),
            is_active=activate,
            metrics_json=json.dumps(metrics),
            feature_list_json=json.dumps(FEATURE_COLUMNS),
            description=f"Trained on dataset #{dataset.id} ({dataset.name})",
        )
        db.add(ml_model)
        db.flush()

        run.model_id = ml_model.id
        run.status = TrainingStatus.completed
        run.accuracy = metrics["accuracy"]
        run.precision = metrics["precision"]
        run.recall = metrics["recall"]
        run.f1_score = metrics["f1_score"]
        run.duration_seconds = duration
        run.confusion_matrix_json = json.dumps(metrics["confusion_matrix"])
        run.metrics_json = json.dumps(metrics)

        db.add(
            AuditLog(
                actor_id=user_id,
                action="ml.train",
                resource_type="ml_model",
                resource_id=str(ml_model.id),
                detail=f"type={model_type.value} f1={metrics['f1_score']:.4f}",
                success=True,
            )
        )
        db.commit()
        db.refresh(ml_model)
        db.refresh(run)
        return {
            "model": ml_model,
            "training_run": run,
            "metrics": metrics,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Training failed")
        db.rollback()
        run = db.query(TrainingRun).filter(TrainingRun.id == run.id).first()
        if run:
            run.status = TrainingStatus.failed
            run.error_message = str(exc)[:1000]
            db.commit()
        raise


def activate_model(db: Session, model_id: int, user_id: Optional[int]) -> MLModel:
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise FileNotFoundError("Model not found")
    db.query(MLModel).filter(MLModel.is_active.is_(True)).update({"is_active": False})
    model.is_active = True
    db.add(
        AuditLog(
            actor_id=user_id,
            action="ml.activate",
            resource_type="ml_model",
            resource_id=str(model.id),
            detail=model.name,
            success=True,
        )
    )
    db.commit()
    db.refresh(model)
    return model


def get_active_model(db: Session) -> Optional[MLModel]:
    return db.query(MLModel).filter(MLModel.is_active.is_(True)).first()


def predict_pcap_flows(
    db: Session,
    *,
    pcap_id: Optional[int] = None,
    limit: int = 500,
    user_id: Optional[int] = None,
) -> dict:
    active = get_active_model(db)
    if not active or not active.stored_path or not Path(active.stored_path).exists():
        raise RuntimeError("No active trained model. Train and activate a model first.")

    q = db.query(TrafficRecord).order_by(TrafficRecord.id.desc())
    if pcap_id is not None:
        q = q.filter(TrafficRecord.pcap_id == pcap_id)
    records = q.limit(limit).all()
    if not records:
        return {"predictions": 0, "attacks": 0, "model_id": active.id, "items": []}

    results = predict_traffic_records(Path(active.stored_path), records)
    created = []
    attacks = 0
    for record, result in zip(records, results):
        if result["predicted_label"] == "attack":
            attacks += 1
            record.label = TrafficLabel.attack
        elif record.label == TrafficLabel.unknown:
            record.label = TrafficLabel.normal

        event = (
            db.query(NetworkEvent)
            .filter(NetworkEvent.traffic_record_id == record.id)
            .first()
        )
        if event and result["predicted_label"] == "attack":
            event.is_suspicious = True
            if not event.summary.startswith("ML:"):
                event.summary = f"ML: {result['attack_category']} (conf={result['confidence']:.2f})"

        pred = Prediction(
            model_id=active.id,
            network_event_id=event.id if event else None,
            traffic_record_id=record.id,
            predicted_label=result["predicted_label"],
            attack_category=result["attack_category"],
            confidence=result["confidence"],
            anomaly_score=result["anomaly_score"],
            severity=result["severity"],
            evidence_json=json.dumps(
                {
                    "source_ip": record.source_ip,
                    "dest_ip": record.dest_ip,
                    "source_port": record.source_port,
                    "dest_port": record.dest_port,
                    "protocol": record.protocol,
                    "packet_count": record.packet_count,
                    "bytes_transferred": record.bytes_transferred,
                    "model": active.name,
                    "model_type": active.model_type.value,
                }
            ),
        )
        db.add(pred)
        created.append(pred)

    db.add(
        AuditLog(
            actor_id=user_id,
            action="ml.predict",
            resource_type="pcap" if pcap_id else "traffic",
            resource_id=str(pcap_id or ""),
            detail=f"predictions={len(created)} attacks={attacks} model={active.id}",
            success=True,
        )
    )
    db.commit()
    for p in created:
        db.refresh(p)

    automation = None
    try:
        from app.services.automation.pipeline import process_predictions_batch

        attack_ids = [p.id for p in created if p.predicted_label == "attack"]
        if attack_ids:
            automation = process_predictions_batch(db, prediction_ids=attack_ids, user_id=user_id)
    except Exception:  # noqa: BLE001
        logger.exception("Automation pipeline after predict failed")

    return {
        "predictions": len(created),
        "attacks": attacks,
        "model_id": active.id,
        "model_name": active.name,
        "automation": automation,
    }
