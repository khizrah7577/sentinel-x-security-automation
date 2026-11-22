"""Security incident listing (investigation/response expanded in later phases)."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.deps import CurrentUser, DbSession
from app.models.incident import ApprovalStatus, ResponseRecommendation, SecurityIncident

router = APIRouter(prefix="/incidents", tags=["incidents"])


class IncidentOut(BaseModel):
    id: int
    title: str
    description: str
    severity: str
    status: str
    source_ip: str
    dest_ip: str
    attack_category: str
    is_demo: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RecommendationOut(BaseModel):
    id: int
    incident_id: int
    action_type: str
    rationale: str
    approval_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[IncidentOut])
def list_incidents(
    _: CurrentUser,
    db: DbSession,
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    q = db.query(SecurityIncident).order_by(SecurityIncident.id.desc())
    if severity:
        q = q.filter(SecurityIncident.severity == severity)
    return q.limit(limit).all()


@router.get("/approvals/pending", response_model=list[RecommendationOut])
def pending_approvals(_: CurrentUser, db: DbSession):
    return (
        db.query(ResponseRecommendation)
        .filter(ResponseRecommendation.approval_status == ApprovalStatus.pending)
        .order_by(ResponseRecommendation.id.desc())
        .all()
    )
