"""Dashboard statistics from real DB data."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.models.incident import ApprovalStatus, ResponseRecommendation, SecurityIncident, Severity
from app.models.ml import MLModel
from app.models.network import NetworkEvent, TrafficLabel, TrafficRecord
from app.schemas.common import DashboardStats
from app.services import secrets as secret_store

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(_: CurrentUser, db: DbSession):
    settings = get_settings()
    total_events = db.query(NetworkEvent).count()
    normal = (
        db.query(TrafficRecord).filter(TrafficRecord.label == TrafficLabel.normal).count()
        + db.query(NetworkEvent).filter(NetworkEvent.is_suspicious.is_(False)).count()
    )
    # Prefer traffic labels when present; fall back to event flags
    suspicious = db.query(NetworkEvent).filter(NetworkEvent.is_suspicious.is_(True)).count()
    attacks = (
        db.query(TrafficRecord).filter(TrafficRecord.label == TrafficLabel.attack).count()
    )
    critical = (
        db.query(SecurityIncident)
        .filter(SecurityIncident.severity == Severity.critical)
        .count()
    )
    pending = (
        db.query(ResponseRecommendation)
        .filter(ResponseRecommendation.approval_status == ApprovalStatus.pending)
        .count()
    )
    models = db.query(MLModel).count()
    active = db.query(MLModel).filter(MLModel.is_active.is_(True)).first()
    ai = secret_store.openai_status()

    return DashboardStats(
        total_network_events=total_events,
        normal_traffic=normal,
        suspicious_traffic=suspicious,
        detected_attacks=attacks,
        critical_incidents=critical,
        pending_approvals=pending,
        ml_models=models,
        active_model=active.name if active else None,
        ai_configured=ai["configured"],
        monitoring_mode=settings.monitoring_mode,
    )
