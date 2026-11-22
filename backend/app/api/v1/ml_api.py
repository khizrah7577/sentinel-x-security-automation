"""ML datasets, training, activation, and prediction APIs."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.deps import AdminUser, CurrentUser, DbSession
from app.ml.preprocessing import DatasetPrepError
from app.models.ml import Dataset, MLModel, ModelType, Prediction, TrainingRun
from app.services import ml_service

router = APIRouter(prefix="/ml", tags=["ml"])


def _reject_heavy_training_if_cloud() -> None:
    settings = get_settings()
    if settings.cloud_lightweight or settings.disable_heavy_ml_training:
        raise HTTPException(
            status_code=403,
            detail=(
                "Heavy ML training is disabled on this cloud/lightweight deployment. "
                "Use pre-trained models for inference, or train locally and upload artifacts."
            ),
        )


class DatasetOut(BaseModel):
    id: int
    name: str
    source: str
    row_count: int
    column_count: int
    status: str
    missing_values: int
    duplicate_records: int
    label_distribution_json: str
    notes: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelOut(BaseModel):
    id: int
    name: str
    model_type: str
    version: str
    is_active: bool
    metrics_json: str
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TrainingRunOut(BaseModel):
    id: int
    dataset_id: Optional[int]
    model_id: Optional[int]
    model_type: str
    status: str
    accuracy: Optional[float]
    precision: Optional[float]
    recall: Optional[float]
    f1_score: Optional[float]
    duration_seconds: Optional[float]
    confusion_matrix_json: str
    error_message: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PredictionOut(BaseModel):
    id: int
    predicted_label: str
    attack_category: str
    confidence: float
    anomaly_score: Optional[float]
    severity: str
    model_id: Optional[int]
    network_event_id: Optional[int]
    traffic_record_id: Optional[int]
    evidence_json: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TrainRequest(BaseModel):
    model_type: ModelType = ModelType.random_forest
    dataset_id: Optional[int] = None
    activate: bool = True


class PredictRequest(BaseModel):
    pcap_id: Optional[int] = None
    limit: int = Field(default=500, ge=1, le=5000)


@router.get("/datasets", response_model=list[DatasetOut])
def list_datasets(_: CurrentUser, db: DbSession, limit: int = Query(50, ge=1, le=200)):
    return db.query(Dataset).order_by(Dataset.id.desc()).limit(limit).all()


@router.post("/datasets/baseline", response_model=DatasetOut)
def create_baseline_dataset(_: AdminUser, db: DbSession):
    return ml_service.ensure_baseline_dataset(db)


@router.post("/datasets/import", response_model=DatasetOut)
async def import_dataset(
    admin: AdminUser,
    db: DbSession,
    file: UploadFile = File(...),
    name: Optional[str] = None,
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV datasets are supported")
    settings = get_settings()
    dest_dir = Path(settings.dataset_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / Path(file.filename).name
    data = await file.read()
    if len(data) > 200 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="CSV too large (max 200 MB)")
    dest.write_bytes(data)
    try:
        return ml_service.import_csv_dataset(
            db,
            name=name or Path(file.filename).stem,
            stored_path=dest,
            source="csv_upload",
            notes=f"Uploaded by user #{admin.id}",
        )
    except DatasetPrepError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/models", response_model=list[ModelOut])
def list_models(_: CurrentUser, db: DbSession):
    return db.query(MLModel).order_by(MLModel.id.desc()).all()


@router.get("/training-runs", response_model=list[TrainingRunOut])
def list_training_runs(_: CurrentUser, db: DbSession, limit: int = Query(50, ge=1, le=200)):
    return db.query(TrainingRun).order_by(TrainingRun.id.desc()).limit(limit).all()


@router.get("/predictions", response_model=list[PredictionOut])
def list_predictions(
    _: CurrentUser,
    db: DbSession,
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
):
    q = db.query(Prediction).order_by(Prediction.id.desc())
    if severity:
        q = q.filter(Prediction.severity == severity)
    return q.limit(limit).all()


@router.get("/status")
def ml_status(_: CurrentUser, db: DbSession):
    active = db.query(MLModel).filter(MLModel.is_active.is_(True)).first()
    return {
        "models_count": db.query(MLModel).count(),
        "datasets_count": db.query(Dataset).count(),
        "predictions_count": db.query(Prediction).count(),
        "active_model": active.name if active else None,
        "active_model_id": active.id if active else None,
        "training_available": True,
        "cicids_downloaded": False,
        "message": (
            f"Active model: {active.name}"
            if active
            else "No trained models yet. Use Train on the Models page (synthetic baseline dataset)."
        ),
    }


@router.post("/train")
def train(payload: TrainRequest, admin: AdminUser, db: DbSession):
    _reject_heavy_training_if_cloud()
    try:
        result = ml_service.train_model(
            db,
            model_type=payload.model_type,
            dataset_id=payload.dataset_id,
            user_id=admin.id,
            activate=payload.activate,
        )
        model = result["model"]
        run = result["training_run"]
        return {
            "model": ModelOut.model_validate(model),
            "training_run": TrainingRunOut.model_validate(run),
            "metrics": result["metrics"],
        }
    except DatasetPrepError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Training failed: {exc}") from exc


@router.post("/models/{model_id}/activate", response_model=ModelOut)
def activate(model_id: int, admin: AdminUser, db: DbSession):
    try:
        return ml_service.activate_model(db, model_id=model_id, user_id=admin.id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/predict")
def predict(payload: PredictRequest, user: CurrentUser, db: DbSession):
    try:
        return ml_service.predict_pcap_flows(
            db,
            pcap_id=payload.pcap_id,
            limit=payload.limit,
            user_id=user.id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/train-all")
def train_all(admin: AdminUser, db: DbSession, dataset_id: Optional[int] = None):
    """Train RF, SVM, and Isolation Forest; activate the best F1 model."""
    _reject_heavy_training_if_cloud()
    results = []
    best = None
    for mt in (ModelType.random_forest, ModelType.svm, ModelType.isolation_forest):
        try:
            out = ml_service.train_model(
                db,
                model_type=mt,
                dataset_id=dataset_id,
                user_id=admin.id,
                activate=False,
            )
            results.append(
                {
                    "model_type": mt.value,
                    "model_id": out["model"].id,
                    "metrics": out["metrics"],
                }
            )
            f1 = out["metrics"].get("f1_score", 0.0)
            if best is None or f1 > best[0]:
                best = (f1, out["model"].id)
        except Exception as exc:  # noqa: BLE001
            results.append({"model_type": mt.value, "error": str(exc)})

    activated = None
    if best:
        activated = ml_service.activate_model(db, model_id=best[1], user_id=admin.id)
    return {
        "results": results,
        "activated_model_id": activated.id if activated else None,
        "activated_model_name": activated.name if activated else None,
    }
