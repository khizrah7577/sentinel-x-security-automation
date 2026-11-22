"""Evaluate TRIGGER → CONDITION → ACTION automation workflows."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.automation import AutomationWorkflow, WorkflowExecution, WorkflowTrigger
from app.models.incident import (
    ApprovalStatus,
    ResponseActionType,
    ResponseRecommendation,
)
from app.response.actions import DISRUPTIVE_ACTIONS
from app.services.automation.notifications import create_notification

logger = logging.getLogger(__name__)

SEVERITY_RANK = {
    "informational": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def _parse_json(raw: str, default: Any):
    try:
        return json.loads(raw or "") or default
    except json.JSONDecodeError:
        return default


def _sev_rank(value: str) -> int:
    return SEVERITY_RANK.get((value or "").lower(), 0)


def conditions_match(conditions: list[dict], ctx: dict[str, Any]) -> bool:
    if not conditions:
        return True
    for cond in conditions:
        field = (cond.get("field") or "").lower()
        op = (cond.get("op") or "eq").lower()
        expected = cond.get("value")
        actual = ctx.get(field)
        if field == "severity":
            if op in ("gte", ">="):
                if _sev_rank(str(actual)) < _sev_rank(str(expected)):
                    return False
            elif op in ("eq", "=="):
                if str(actual).lower() != str(expected).lower():
                    return False
            else:
                if str(actual).lower() != str(expected).lower():
                    return False
        elif field == "ml_confidence" or field == "confidence":
            try:
                a = float(actual or 0)
                e = float(expected or 0)
            except (TypeError, ValueError):
                return False
            if op in ("gte", ">="):
                if a < e:
                    return False
            elif op in ("lte", "<="):
                if a > e:
                    return False
            elif a != e:
                return False
        elif field == "attack_category":
            if str(actual or "").lower() != str(expected or "").lower():
                return False
        elif field == "source_ip":
            if str(actual or "") != str(expected or ""):
                return False
        elif field == "destination_port" or field == "dest_port":
            try:
                if int(actual or 0) != int(expected or 0):
                    return False
            except (TypeError, ValueError):
                return False
        elif field == "investigation_status":
            if str(actual or "").lower() != str(expected or "").lower():
                return False
        elif field == "event_frequency":
            try:
                if int(ctx.get("event_frequency") or 0) < int(expected or 0):
                    return False
            except (TypeError, ValueError):
                return False
        else:
            if str(actual) != str(expected):
                return False
    return True


def _run_action(db: Session, action: dict, ctx: dict[str, Any], user_id: Optional[int]) -> dict:
    atype = action.get("type") or action.get("action")
    out: dict[str, Any] = {"type": atype, "ok": False}

    if atype == "send_notification":
        create_notification(
            db,
            title=str(action.get("title") or "SENTINEL X automation"),
            body=str(action.get("body") or ctx.get("summary") or ""),
            category="automation",
            severity=str(action.get("severity") or ctx.get("severity") or "info"),
            link=str(action.get("link") or "/intelligence"),
            notify_admins=True,
            meta={"context": {k: ctx.get(k) for k in ("prediction_id", "incident_id", "investigation_id")}},
        )
        out["ok"] = True
        out["detail"] = "notification_created"
        return out

    if atype == "create_incident":
        from app.services.investigation_service import ensure_incident_for_prediction

        pred_id = ctx.get("prediction_id")
        if not pred_id:
            out["detail"] = "missing_prediction_id"
            return out
        inc = ensure_incident_for_prediction(db, int(pred_id))
        ctx["incident_id"] = inc.id
        out["ok"] = True
        out["incident_id"] = inc.id
        return out

    if atype == "start_investigation":
        from app.services.investigation_service import run_investigation

        pred_id = ctx.get("prediction_id")
        incident_id = ctx.get("incident_id")
        if not pred_id and not incident_id:
            out["detail"] = "missing_prediction_or_incident"
            return out
        result = run_investigation(
            db,
            prediction_id=int(pred_id) if pred_id else None,
            incident_id=int(incident_id) if incident_id else None,
            user_id=user_id,
        )
        ctx["investigation_id"] = result.get("investigation_id")
        out["ok"] = True
        out["investigation_id"] = result.get("investigation_id")
        return out

    if atype == "generate_report":
        create_notification(
            db,
            title="Security report ready",
            body="A report snapshot was requested by automation. Download from Reports.",
            category="report",
            severity="info",
            link="/reports",
            notify_admins=True,
        )
        out["ok"] = True
        out["detail"] = "report_notification"
        return out

    if atype == "create_response_recommendation":
        incident_id = ctx.get("incident_id")
        if not incident_id:
            out["detail"] = "missing_incident_id"
            return out
        action_type = action.get("action_type") or "create_alert"
        try:
            rat = ResponseActionType(action_type)
        except ValueError:
            rat = ResponseActionType.create_alert
        if rat in DISRUPTIVE_ACTIONS:
            # Always create as pending approval — never auto-block from uncertain ML alone
            pass
        rec = ResponseRecommendation(
            incident_id=int(incident_id),
            investigation_id=ctx.get("investigation_id"),
            action_type=rat,
            parameters_json=json.dumps(
                {
                    "target_ip": ctx.get("source_ip") or "",
                    "lab_only": True,
                    "temporary": True,
                    "from_automation": True,
                }
            ),
            rationale=str(action.get("rationale") or ctx.get("summary") or "Automation recommendation"),
            approval_status=ApprovalStatus.pending,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        out["ok"] = True
        out["recommendation_id"] = rec.id
        return out

    if atype == "request_approval":
        create_notification(
            db,
            title="Approval requested",
            body=str(action.get("body") or "A response recommendation requires administrator approval."),
            category="approval",
            severity="warning",
            link="/response",
            notify_admins=True,
        )
        out["ok"] = True
        return out

    if atype == "execute_approved_action":
        # Only execute already-approved recommendations — never skip approval for disruptive
        from app.services.response_service import execute_recommendation
        from app.models.user import User

        rec_id = action.get("recommendation_id") or ctx.get("recommendation_id")
        if not rec_id:
            out["detail"] = "missing_recommendation_id"
            return out
        admin = db.query(User).filter(User.id == user_id).first() if user_id else None
        if not admin:
            out["detail"] = "admin_required"
            return out
        try:
            executed = execute_recommendation(db, recommendation_id=int(rec_id), user=admin)
            out["ok"] = True
            out["executed_id"] = getattr(executed, "id", None)
        except Exception as exc:  # noqa: BLE001
            out["detail"] = str(exc)
        return out

    out["detail"] = f"unknown_action:{atype}"
    return out


def evaluate_workflows(
    db: Session,
    *,
    trigger: WorkflowTrigger | str,
    context: dict[str, Any],
    user_id: Optional[int] = None,
) -> list[dict]:
    trigger_val = trigger.value if isinstance(trigger, WorkflowTrigger) else str(trigger)
    try:
        trigger_enum = trigger if isinstance(trigger, WorkflowTrigger) else WorkflowTrigger(trigger_val)
    except ValueError:
        trigger_enum = None
    q = db.query(AutomationWorkflow).filter(AutomationWorkflow.enabled.is_(True))
    if trigger_enum is not None:
        q = q.filter(AutomationWorkflow.trigger == trigger_enum)
    else:
        q = q.filter(False)
    workflows = q.all()
    results = []
    for wf in workflows:
        started = time.perf_counter()
        conditions = _parse_json(wf.conditions_json, [])
        actions = _parse_json(wf.actions_json, [])
        status = "skipped"
        error = ""
        action_results: list[dict] = []
        try:
            if not conditions_match(conditions if isinstance(conditions, list) else [], context):
                status = "conditions_not_met"
            else:
                for act in actions if isinstance(actions, list) else []:
                    action_results.append(_run_action(db, act, context, user_id))
                status = "completed" if all(a.get("ok") for a in action_results) or not action_results else "partial"
        except Exception as exc:  # noqa: BLE001
            status = "failed"
            error = str(exc)
            logger.exception("Workflow %s failed", wf.id)

        duration = int((time.perf_counter() - started) * 1000)
        exe = WorkflowExecution(
            workflow_id=wf.id,
            trigger=trigger_val,
            status=status,
            context_json=json.dumps(context, default=str),
            result_json=json.dumps({"actions": action_results}, default=str),
            error_message=error,
            duration_ms=duration,
        )
        db.add(exe)
        wf.run_count = int(wf.run_count or 0) + 1
        from datetime import datetime, timezone

        wf.last_run_at = datetime.now(timezone.utc)
        wf.last_status = status
        db.commit()
        results.append({"workflow_id": wf.id, "name": wf.name, "status": status, "error": error})
    return results
