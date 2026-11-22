"""Response Center: modes, approvals, execution, rollback, audit."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.deps import AdminUser, CurrentUser, DbSession
from app.models.audit import AuditLog
from app.models.incident import (
    ApprovalStatus,
    ExecutedAction,
    FirewallRule,
    ResponseRecommendation,
)
from app.models.user import AppSetting
from app.response.actions import ActionError, LOW_RISK_ACTIONS, DISRUPTIVE_ACTIONS
from app.services import response_service

router = APIRouter(prefix="/response", tags=["response"])


class RecommendationOut(BaseModel):
    id: int
    incident_id: int
    action_type: str
    rationale: str
    approval_status: str
    rejection_reason: str = ""
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    parameters_json: str = "{}"
    created_at: datetime

    model_config = {"from_attributes": True}


class ExecutedOut(BaseModel):
    id: int
    recommendation_id: Optional[int]
    action_type: str
    success: bool
    verification_result: str
    rollback_available: bool
    rolled_back: bool
    error_message: str = ""
    parameters_json: str = "{}"
    created_at: datetime

    model_config = {"from_attributes": True}


class FirewallOut(BaseModel):
    id: int
    target_ip: str
    direction: str
    action: str
    is_temporary: bool
    is_active: bool
    lab_only: bool
    notes: str
    expires_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditOut(BaseModel):
    id: int
    action: str
    resource_type: str
    resource_id: str
    detail: str
    success: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ModeUpdate(BaseModel):
    mode: str


class RejectBody(BaseModel):
    reason: str = Field(default="", max_length=1000)


class ApproveBody(BaseModel):
    execute_now: bool = True


@router.get("/mode")
def response_mode(_: CurrentUser, db: DbSession):
    mode = response_service.get_response_mode(db)
    return {
        "mode": mode,
        "modes": sorted(response_service.VALID_MODES),
        "description": {
            "manual": "Detect and recommend only; administrator acts manually after approval record.",
            "approval_required": "Prepare response and wait for admin approval before execution.",
            "restricted_automatic": "Only low-risk allowlisted actions may auto-run in the lab.",
        },
        "low_risk_actions": [a.value for a in LOW_RISK_ACTIONS],
        "disruptive_actions": [a.value for a in DISRUPTIVE_ACTIONS],
    }


@router.put("/mode")
def set_mode(payload: ModeUpdate, admin: AdminUser, db: DbSession):
    try:
        mode = response_service.set_response_mode(db, payload.mode, user_id=admin.id)
        return {"mode": mode}
    except ActionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/recommendations", response_model=list[RecommendationOut])
def list_recommendations(
    _: CurrentUser,
    db: DbSession,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    q = db.query(ResponseRecommendation).order_by(ResponseRecommendation.id.desc())
    if status:
        q = q.filter(ResponseRecommendation.approval_status == status)
    return q.limit(limit).all()


@router.post("/recommendations/{recommendation_id}/approve")
def approve(recommendation_id: int, payload: ApproveBody, admin: AdminUser, db: DbSession):
    try:
        result = response_service.approve_recommendation(
            db,
            recommendation_id=recommendation_id,
            user=admin,
            execute_now=payload.execute_now,
        )
        executed = result["executed"]
        return {
            "recommendation": RecommendationOut.model_validate(result["recommendation"]),
            "executed": ExecutedOut.model_validate(executed) if executed else None,
            "mode": result["mode"],
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ActionError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/recommendations/{recommendation_id}/reject", response_model=RecommendationOut)
def reject(recommendation_id: int, payload: RejectBody, admin: AdminUser, db: DbSession):
    try:
        return response_service.reject_recommendation(
            db,
            recommendation_id=recommendation_id,
            user=admin,
            reason=payload.reason,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ActionError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/recommendations/{recommendation_id}/execute", response_model=ExecutedOut)
def execute(recommendation_id: int, admin: AdminUser, db: DbSession):
    try:
        return response_service.execute_recommendation(
            db, recommendation_id=recommendation_id, user=admin
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ActionError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/executed/{executed_id}/rollback", response_model=ExecutedOut)
def rollback(executed_id: int, admin: AdminUser, db: DbSession):
    try:
        return response_service.rollback_executed_action(
            db, executed_id=executed_id, user=admin
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ActionError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/executed", response_model=list[ExecutedOut])
def list_executed(_: CurrentUser, db: DbSession, limit: int = Query(50, ge=1, le=200)):
    return db.query(ExecutedAction).order_by(ExecutedAction.id.desc()).limit(limit).all()


@router.get("/firewall-rules", response_model=list[FirewallOut])
def list_firewall_rules(_: CurrentUser, db: DbSession, active_only: bool = False):
    q = db.query(FirewallRule).order_by(FirewallRule.id.desc())
    if active_only:
        q = q.filter(FirewallRule.is_active.is_(True))
    return q.all()


@router.get("/audit", response_model=list[AuditOut])
def list_audit(_: CurrentUser, db: DbSession, limit: int = Query(100, ge=1, le=500)):
    return db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()


@router.get("/summary")
def response_summary(_: CurrentUser, db: DbSession):
    return {
        "pending": db.query(ResponseRecommendation)
        .filter(ResponseRecommendation.approval_status == ApprovalStatus.pending)
        .count(),
        "approved": db.query(ResponseRecommendation)
        .filter(ResponseRecommendation.approval_status == ApprovalStatus.approved)
        .count(),
        "rejected": db.query(ResponseRecommendation)
        .filter(ResponseRecommendation.approval_status == ApprovalStatus.rejected)
        .count(),
        "executed": db.query(ExecutedAction).count(),
        "active_firewall_rules": db.query(FirewallRule)
        .filter(FirewallRule.is_active.is_(True))
        .count(),
        "mode": response_service.get_response_mode(db),
    }
