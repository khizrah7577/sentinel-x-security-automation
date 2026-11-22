"""Dataset, model, training, and prediction models."""

from __future__ import annotations

import enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class DatasetStatus(str, enum.Enum):
    imported = "imported"
    preprocessing = "preprocessing"
    ready = "ready"
    failed = "failed"


class ModelType(str, enum.Enum):
    random_forest = "random_forest"
    svm = "svm"
    isolation_forest = "isolation_forest"


class TrainingStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class Dataset(Base, TimestampMixin):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(128), default="custom")
    stored_path: Mapped[str] = mapped_column(String(1024), default="")
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    column_count: Mapped[int] = mapped_column(Integer, default=0)
    label_distribution_json: Mapped[str] = mapped_column(Text, default="{}")
    missing_values: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_records: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[DatasetStatus] = mapped_column(
        Enum(DatasetStatus, name="dataset_status"),
        default=DatasetStatus.imported,
    )
    notes: Mapped[str] = mapped_column(Text, default="")

    training_runs: Mapped[list["TrainingRun"]] = relationship(back_populates="dataset")


class MLModel(Base, TimestampMixin):
    __tablename__ = "ml_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_type: Mapped[ModelType] = mapped_column(Enum(ModelType, name="model_type"))
    version: Mapped[str] = mapped_column(String(64), default="1.0.0")
    stored_path: Mapped[str] = mapped_column(String(1024), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    feature_list_json: Mapped[str] = mapped_column(Text, default="[]")
    description: Mapped[str] = mapped_column(Text, default="")

    training_runs: Mapped[list["TrainingRun"]] = relationship(back_populates="model")
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="model")


class TrainingRun(Base, TimestampMixin):
    __tablename__ = "training_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("datasets.id"), nullable=True)
    model_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ml_models.id"), nullable=True)
    model_type: Mapped[ModelType] = mapped_column(Enum(ModelType, name="training_model_type"))
    status: Mapped[TrainingStatus] = mapped_column(
        Enum(TrainingStatus, name="training_status"),
        default=TrainingStatus.pending,
    )
    accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    precision: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recall: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    f1_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confusion_matrix_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")

    dataset: Mapped[Optional[Dataset]] = relationship(back_populates="training_runs")
    model: Mapped[Optional[MLModel]] = relationship(back_populates="training_runs")


class Prediction(Base, TimestampMixin):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ml_models.id"), index=True)
    network_event_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("network_events.id"), index=True, nullable=True
    )
    traffic_record_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("traffic_records.id"), nullable=True
    )
    predicted_label: Mapped[str] = mapped_column(String(64), default="")
    attack_category: Mapped[str] = mapped_column(String(128), default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    anomaly_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    severity: Mapped[str] = mapped_column(String(32), default="informational")
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")

    model: Mapped[Optional[MLModel]] = relationship(back_populates="predictions")
