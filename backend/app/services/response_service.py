"""Response approval, execution, rollback, and mode management."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.incident import (
    ApprovalStatus,
    ExecutedAction,
    IncidentStatus,
    ResponseActionType,
    ResponseRecommendation,
    SecurityIncident,
)
from app.models.user import AppSetting, User, UserRole
from app.response.actions import (
    DISRUPTIVE_ACTIONS,
    LOW_RISK_ACTIONS,
    ActionError,
    execute_allowlisted_action,
    parse_params,
    rollback_execution,
)

logger = logging.getLogger(__name__)

VALID_MODES = {"manual", "approval_required", "restricted_automatic"}


def get_response_mode(db: Session) -> str:
    row = db.query(AppSetting).filter(AppSetting.key == "response_mode").first()
    return row.value if row else "approval_required"


def set_response_mode(db: Session, mode: str, user_id: Optional[int]) -> str:
    if mode not in VALID_MODES:
        raise ActionError(f"Invalid mode. Allowed: {sorted(VALID_MODES)}")
    row = db.query(AppSetting).filter(AppSetting.key == "response_mode").first()
    if row:
        row.value = mode
    else:
        db.add(AppSetting(key="response_mode", value=mode, description="Response automation mode"))
    db.add(
        AuditLog(
            actor_id=user_id,
            action="response.mode_set",
            resource_type="settings",
            detail=mode,
            success=True,
        )
    )
    db.commit()
    return mode


def _require_admin(user: User) -> None:
    if user.role != UserRole.admin:
        raise PermissionError("Admin role required for response approvals/execution")


def approve_recommendation(
    db: Session,
    *,
    recommendation_id: int,
    user: User,
    execute_now: bool = True,
) -> dict:
    _require_admin(user)
    rec = db.query(ResponseRecommendation).filter(ResponseRecommendation.id == recommendation_id).first()
    if not rec:
        raise FileNotFoundError("Recommendation not found")
    if rec.approval_status != ApprovalStatus.pending:
        raise ActionError(f"Recommendation is not pending (status={rec.approval_status.value})")

    mode = get_response_mode(db)
    if mode == "manual":
        # Approval records intent only; no automatic execution
        execute_now = False

    rec.approval_status = ApprovalStatus.approved
    rec.approved_by_id = user.id
    rec.approved_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            actor_id=user.id,
            action="response.approve",
            resource_type="recommendation",
            resource_id=str(rec.id),
            detail=rec.action_type.value,
            success=True,
        )
    )
    db.commit()
    db.refresh(rec)

    try:
        from app.models.automation import WorkflowTrigger
        from app.services.automation.notifications import create_notification
        from app.services.automation.workflow_engine import evaluate_workflows

        create_notification(
            db,
            title="Response approval received",
            body=f"Recommendation #{rec.id} ({rec.action_type.value}) approved by {user.email}",
            category="approval",
            severity="info",
            link="/response",
            notify_admins=True,
            meta={"recommendation_id": rec.id, "incident_id": rec.incident_id},
        )
        evaluate_workflows(
            db,
            trigger=WorkflowTrigger.response_approval,
            context={
                "recommendation_id": rec.id,
                "incident_id": rec.incident_id,
                "investigation_id": rec.investigation_id,
                "summary": f"Approval for {rec.action_type.value}",
            },
            user_id=user.id,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Approval automation hook skipped")

    executed = None
    if execute_now:
        executed = execute_recommendation(db, recommendation_id=rec.id, user=user)
    return {"recommendation": rec, "executed": executed, "mode": mode}


def reject_recommendation(
    db: Session,
    *,
    recommendation_id: int,
    user: User,
    reason: str = "",
) -> ResponseRecommendation:
    _require_admin(user)
    rec = db.query(ResponseRecommendation).filter(ResponseRecommendation.id == recommendation_id).first()
    if not rec:
        raise FileNotFoundError("Recommendation not found")
    if rec.approval_status != ApprovalStatus.pending:
        raise ActionError(f"Recommendation is not pending (status={rec.approval_status.value})")
    rec.approval_status = ApprovalStatus.rejected
    rec.rejection_reason = reason or "Rejected by administrator"
    rec.approved_by_id = user.id
    rec.approved_at = datetime.now(timezone.utc)
    incident = db.query(SecurityIncident).filter(SecurityIncident.id == rec.incident_id).first()
    if incident and incident.status == IncidentStatus.awaiting_approval:
        incident.status = IncidentStatus.open
    db.add(
        AuditLog(
            actor_id=user.id,
            action="response.reject",
            resource_type="recommendation",
            resource_id=str(rec.id),
            detail=rec.rejection_reason[:500],
            success=True,
        )
    )
    db.commit()
    db.refresh(rec)
    return rec


def execute_recommendation(db: Session, *, recommendation_id: int, user: User) -> ExecutedAction:
    _require_admin(user)
    rec = db.query(ResponseRecommendation).filter(ResponseRecommendation.id == recommendation_id).first()
    if not rec:
        raise FileNotFoundError("Recommendation not found")

    mode = get_response_mode(db)
    if rec.approval_status == ApprovalStatus.pending:
        if mode == "restricted_automatic" and rec.action_type in LOW_RISK_ACTIONS:
            rec.approval_status = ApprovalStatus.auto_executed
            rec.approved_by_id = user.id
            rec.approved_at = datetime.now(timezone.utc)
        else:
            raise ActionError("Recommendation requires approval before execution")
    elif rec.approval_status == ApprovalStatus.rejected:
        raise ActionError("Cannot execute a rejected recommendation")

    if mode == "restricted_automatic" and rec.action_type in DISRUPTIVE_ACTIONS:
        if rec.approval_status != ApprovalStatus.approved:
            raise ActionError(
                "Disruptive actions cannot auto-run; approve explicitly in approval_required/manual flow"
            )

    incident = db.query(SecurityIncident).filter(SecurityIncident.id == rec.incident_id).first()
    params = parse_params(rec.parameters_json)

    try:
        result = execute_allowlisted_action(
            db,
            action_type=rec.action_type,
            parameters=params,
            incident=incident,
            user_id=user.id,
        )
        executed = ExecutedAction(
            recommendation_id=rec.id,
            action_type=rec.action_type,
            parameters_json=json.dumps(result.get("parameters") or params, default=str),
            success=bool(result.get("success")),
            verification_result=str(result.get("verification_result") or ""),
            rollback_available=bool(result.get("rollback_available")),
            rolled_back=False,
            executed_by_id=user.id,
            error_message="",
        )
        if incident and result.get("success") and rec.action_type != ResponseActionType.mark_resolved:
            if incident.status == IncidentStatus.awaiting_approval:
                incident.status = IncidentStatus.responding
        db.add(executed)
        db.add(
            AuditLog(
                actor_id=user.id,
                action="response.execute",
                resource_type="recommendation",
                resource_id=str(rec.id),
                detail=executed.verification_result[:500],
                success=executed.success,
            )
        )
        db.commit()
        db.refresh(executed)
        try:
            from app.services.automation.notifications import create_notification

            create_notification(
                db,
                title="Defensive action succeeded" if executed.success else "Defensive action failed",
                body=executed.verification_result or f"{rec.action_type.value} completed",
                category="response",
                severity="success" if executed.success else "warning",
                link="/response",
                notify_admins=True,
                meta={"executed_id": executed.id, "recommendation_id": rec.id},
            )
        except Exception:  # noqa: BLE001
            logger.exception("Response success notification skipped")
        return executed
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        executed = ExecutedAction(
            recommendation_id=rec.id,
            action_type=rec.action_type,
            parameters_json=json.dumps(params, default=str),
            success=False,
            verification_result="Execution failed",
            rollback_available=False,
            rolled_back=False,
            executed_by_id=user.id,
            error_message=str(exc)[:1000],
        )
        db.add(executed)
        db.add(
            AuditLog(
                actor_id=user.id,
                action="response.execute",
                resource_type="recommendation",
                resource_id=str(rec.id),
                detail=str(exc)[:500],
                success=False,
            )
        )
        db.commit()
        db.refresh(executed)
        return executed


def rollback_executed_action(db: Session, *, executed_id: int, user: User) -> ExecutedAction:
    _require_admin(user)
    executed = db.query(ExecutedAction).filter(ExecutedAction.id == executed_id).first()
    if not executed:
        raise FileNotFoundError("Executed action not found")
    if not executed.rollback_available:
        raise ActionError("Rollback not available for this action")
    if executed.rolled_back:
        raise ActionError("Action already rolled back")
    if not executed.success:
        raise ActionError("Cannot rollback a failed execution")

    rec = None
    incident = None
    if executed.recommendation_id:
        rec = (
            db.query(ResponseRecommendation)
            .filter(ResponseRecommendation.id == executed.recommendation_id)
            .first()
        )
        if rec:
            incident = db.query(SecurityIncident).filter(SecurityIncident.id == rec.incident_id).first()

    params = parse_params(executed.parameters_json)
    result = rollback_execution(
        db,
        action_type=executed.action_type,
        parameters=params,
        incident=incident,
    )
    executed.rolled_back = True
    executed.verification_result = (
        f"{executed.verification_result} | ROLLBACK: {result.get('verification_result')}"
    )
    db.add(
        AuditLog(
            actor_id=user.id,
            action="response.rollback",
            resource_type="executed_action",
            resource_id=str(executed.id),
            detail=str(result.get("verification_result") or "")[:500],
            success=True,
        )
    )
    db.commit()
    db.refresh(executed)
    return executed


def maybe_auto_execute(db: Session, recommendation_id: int, system_user_id: Optional[int] = None) -> Optional[ExecutedAction]:
    """Used after investigation when mode is restricted_automatic and action is low-risk."""
    mode = get_response_mode(db)
    if mode != "restricted_automatic":
        return None
    rec = db.query(ResponseRecommendation).filter(ResponseRecommendation.id == recommendation_id).first()
    if not rec or rec.action_type not in LOW_RISK_ACTIONS:
        return None
    # Create a synthetic admin actor reference if needed — require a real admin user
    admin = db.query(User).filter(User.role == UserRole.admin, User.is_active.is_(True)).first()
    if not admin:
        return None
    return execute_recommendation(db, recommendation_id=rec.id, user=admin)
