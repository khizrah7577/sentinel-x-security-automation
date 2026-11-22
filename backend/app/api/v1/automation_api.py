"""Automation Center APIs — workflows, scheduler, notifications, policies."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.core.security import TokenError, safe_decode_token
from app.database.session import SessionLocal
from app.models.automation import (
    AppNotification,
    AutomationWorkflow,
    NotificationRule,
    ResponseAutomationPolicy,
    ScheduledTask,
    ScheduledTaskRun,
    WorkflowExecution,
    WorkflowTrigger,
)
from app.models.user import User
from app.services.automation import notifications as notif_svc
from app.services.automation.pipeline import process_prediction_automation
from app.services.automation.realtime import hub
from app.services.automation.scheduler_service import execute_task, sync_scheduler_jobs
from app.services.automation.workflow_engine import evaluate_workflows

router = APIRouter(prefix="/automation", tags=["automation"])


class WorkflowIn(BaseModel):
    name: str
    description: str = ""
    enabled: bool = True
    trigger: str
    conditions: list[dict[str, Any]] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)


class WorkflowOut(BaseModel):
    id: int
    name: str
    description: str
    enabled: bool
    trigger: str
    conditions_json: str
    actions_json: str
    last_run_at: Optional[datetime]
    last_status: str
    run_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskPatch(BaseModel):
    enabled: Optional[bool] = None
    cron_or_interval: Optional[str] = None
    name: Optional[str] = None


class PolicyIn(BaseModel):
    name: str
    enabled: bool = True
    action_type: str
    require_approval: bool = True
    allow_auto: bool = False
    min_confidence: float = 0.9
    min_severity: str = "high"
    lab_only: bool = True
    notes: str = ""


class NotifRuleIn(BaseModel):
    name: str
    enabled: bool = True
    event_type: str = "critical_threat"
    min_severity: str = "high"
    notify_admins: bool = True


@router.get("/overview")
def automation_overview(_: CurrentUser, db: DbSession):
    return {
        "workflows_total": db.query(AutomationWorkflow).count(),
        "workflows_enabled": db.query(AutomationWorkflow).filter(AutomationWorkflow.enabled.is_(True)).count(),
        "scheduled_tasks": db.query(ScheduledTask).count(),
        "scheduled_enabled": db.query(ScheduledTask).filter(ScheduledTask.enabled.is_(True)).count(),
        "executions_24h": db.query(WorkflowExecution).count(),
        "unread_notifications": db.query(AppNotification).filter(AppNotification.is_read.is_(False)).count(),
        "policies": db.query(ResponseAutomationPolicy).count(),
        "notification_rules": db.query(NotificationRule).count(),
        "catalog": {
            "triggers": [t.value for t in WorkflowTrigger],
            "condition_fields": [
                "severity",
                "attack_category",
                "ml_confidence",
                "source_ip",
                "destination_port",
                "event_frequency",
                "investigation_status",
            ],
            "actions": [
                "create_incident",
                "start_investigation",
                "generate_report",
                "send_notification",
                "create_response_recommendation",
                "request_approval",
                "execute_approved_action",
            ],
        },
    }


# ---- Workflows ----
@router.get("/workflows", response_model=list[WorkflowOut])
def list_workflows(_: CurrentUser, db: DbSession):
    return db.query(AutomationWorkflow).order_by(AutomationWorkflow.id.desc()).all()


@router.post("/workflows", response_model=WorkflowOut)
def create_workflow(payload: WorkflowIn, user: AdminUser, db: DbSession):
    try:
        trigger = WorkflowTrigger(payload.trigger)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid trigger: {payload.trigger}") from exc
    row = AutomationWorkflow(
        name=payload.name,
        description=payload.description,
        enabled=payload.enabled,
        trigger=trigger,
        conditions_json=json.dumps(payload.conditions),
        actions_json=json.dumps(payload.actions),
        created_by_id=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/workflows/{workflow_id}", response_model=WorkflowOut)
def update_workflow(workflow_id: int, payload: WorkflowIn, _: AdminUser, db: DbSession):
    row = db.query(AutomationWorkflow).filter(AutomationWorkflow.id == workflow_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")
    try:
        row.trigger = WorkflowTrigger(payload.trigger)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row.name = payload.name
    row.description = payload.description
    row.enabled = payload.enabled
    row.conditions_json = json.dumps(payload.conditions)
    row.actions_json = json.dumps(payload.actions)
    db.commit()
    db.refresh(row)
    return row


@router.post("/workflows/{workflow_id}/toggle")
def toggle_workflow(workflow_id: int, _: AdminUser, db: DbSession):
    row = db.query(AutomationWorkflow).filter(AutomationWorkflow.id == workflow_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")
    row.enabled = not row.enabled
    db.commit()
    return {"id": row.id, "enabled": row.enabled}


@router.post("/workflows/{workflow_id}/test")
def test_workflow(workflow_id: int, user: AdminUser, db: DbSession):
    row = db.query(AutomationWorkflow).filter(AutomationWorkflow.id == workflow_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")
    ctx = {
        "prediction_id": None,
        "severity": "high",
        "ml_confidence": 0.95,
        "confidence": 0.95,
        "attack_category": "test",
        "source_ip": "10.0.0.66",
        "dest_port": 80,
        "summary": "Dry-run test context (no fake network traffic persisted)",
        "investigation_status": "completed",
    }
    # Temporarily force evaluate this one only by cloning trigger context
    results = evaluate_workflows(db, trigger=row.trigger, context=ctx, user_id=user.id)
    matched = [r for r in results if r.get("workflow_id") == row.id]
    return {"tested": True, "results": matched or results}


@router.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: int, _: AdminUser, db: DbSession):
    row = db.query(AutomationWorkflow).filter(AutomationWorkflow.id == workflow_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.delete(row)
    db.commit()
    return {"deleted": workflow_id}


@router.get("/history")
def automation_history(_: CurrentUser, db: DbSession, limit: int = Query(50, ge=1, le=200)):
    rows = db.query(WorkflowExecution).order_by(WorkflowExecution.id.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "workflow_id": r.workflow_id,
            "trigger": r.trigger,
            "status": r.status,
            "error_message": r.error_message,
            "duration_ms": r.duration_ms,
            "result_json": r.result_json,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/active")
def active_workflows(_: CurrentUser, db: DbSession):
    return (
        db.query(AutomationWorkflow)
        .filter(AutomationWorkflow.enabled.is_(True))
        .order_by(AutomationWorkflow.id.desc())
        .all()
    )


# ---- Scheduler ----
@router.get("/scheduler")
def list_scheduler(_: CurrentUser, db: DbSession):
    tasks = db.query(ScheduledTask).order_by(ScheduledTask.id.asc()).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "kind": t.kind.value if hasattr(t.kind, "value") else str(t.kind),
            "cron_or_interval": t.cron_or_interval,
            "enabled": t.enabled,
            "last_run_at": t.last_run_at,
            "last_status": t.last_status,
            "last_error": t.last_error,
            "is_running": t.is_running,
        }
        for t in tasks
    ]


@router.patch("/scheduler/{task_id}")
def patch_scheduler(task_id: int, payload: TaskPatch, _: AdminUser, db: DbSession):
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if payload.enabled is not None:
        task.enabled = payload.enabled
    if payload.cron_or_interval is not None:
        task.cron_or_interval = payload.cron_or_interval
    if payload.name is not None:
        task.name = payload.name
    db.commit()
    sync_scheduler_jobs(db)
    return {"id": task.id, "enabled": task.enabled, "cron_or_interval": task.cron_or_interval}


@router.post("/scheduler/{task_id}/run")
def run_scheduler_now(task_id: int, _: AdminUser, db: DbSession):
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    execute_task(task_id)
    db.refresh(task)
    return {"id": task.id, "last_status": task.last_status, "last_error": task.last_error}


@router.get("/scheduler/{task_id}/runs")
def scheduler_runs(task_id: int, _: CurrentUser, db: DbSession, limit: int = 20):
    return (
        db.query(ScheduledTaskRun)
        .filter(ScheduledTaskRun.task_id == task_id)
        .order_by(ScheduledTaskRun.id.desc())
        .limit(limit)
        .all()
    )


# ---- Response policies ----
@router.get("/response-policies")
def list_policies(_: CurrentUser, db: DbSession):
    return db.query(ResponseAutomationPolicy).order_by(ResponseAutomationPolicy.id.desc()).all()


@router.post("/response-policies")
def create_policy(payload: PolicyIn, _: AdminUser, db: DbSession):
    # Disruptive actions must keep require_approval True
    require_approval = payload.require_approval
    allow_auto = payload.allow_auto
    if payload.action_type in {
        "recommend_block_ip",
        "apply_temp_firewall_rule",
        "remove_temp_firewall_rule",
    }:
        require_approval = True
        allow_auto = False
    row = ResponseAutomationPolicy(
        name=payload.name,
        enabled=payload.enabled,
        action_type=payload.action_type,
        require_approval=require_approval,
        allow_auto=allow_auto,
        min_confidence=payload.min_confidence,
        min_severity=payload.min_severity,
        lab_only=True,
        notes=payload.notes
        + (" | Disruptive actions always require approval." if require_approval and not payload.require_approval else ""),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/response-policies/{policy_id}")
def delete_policy(policy_id: int, _: AdminUser, db: DbSession):
    row = db.query(ResponseAutomationPolicy).filter(ResponseAutomationPolicy.id == policy_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(row)
    db.commit()
    return {"deleted": policy_id}


# ---- Notification rules + inbox ----
@router.get("/notification-rules")
def list_notif_rules(_: CurrentUser, db: DbSession):
    return db.query(NotificationRule).order_by(NotificationRule.id.desc()).all()


@router.post("/notification-rules")
def create_notif_rule(payload: NotifRuleIn, _: AdminUser, db: DbSession):
    row = NotificationRule(
        name=payload.name,
        enabled=payload.enabled,
        event_type=payload.event_type,
        min_severity=payload.min_severity,
        notify_admins=payload.notify_admins,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/notifications")
def my_notifications(user: CurrentUser, db: DbSession, unread_only: bool = False):
    rows = notif_svc.list_notifications(db, user_id=user.id, unread_only=unread_only)
    return [
        {
            "id": n.id,
            "title": n.title,
            "body": n.body,
            "category": n.category,
            "severity": n.severity.value if hasattr(n.severity, "value") else n.severity,
            "link": n.link,
            "is_read": n.is_read,
            "created_at": n.created_at,
        }
        for n in rows
    ]


@router.post("/notifications/{notification_id}/read")
def read_one(notification_id: int, user: CurrentUser, db: DbSession):
    n = notif_svc.mark_read(db, notification_id=notification_id, user_id=user.id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"id": n.id, "is_read": n.is_read}


@router.post("/notifications/read-all")
def read_all(user: CurrentUser, db: DbSession):
    return {"updated": notif_svc.mark_all_read(db, user_id=user.id)}


@router.post("/pipeline/prediction/{prediction_id}")
def run_pipeline(prediction_id: int, user: AdminUser, db: DbSession):
    return process_prediction_automation(db, prediction_id=prediction_id, user_id=user.id)


@router.websocket("/ws")
async def automation_ws(websocket: WebSocket):
    """Real-time notification channel. Pass ?token=JWT."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return
    try:
        payload = safe_decode_token(token)
        email = payload.get("sub")
    except TokenError:
        await websocket.close(code=4401)
        return
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user or not user.is_active:
            await websocket.close(code=4401)
            return
    finally:
        db.close()

    await hub.connect(websocket)
    try:
        await websocket.send_text(json.dumps({"type": "connected", "app": "SENTINEL X"}))
        while True:
            # Keepalive / ignore client pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect(websocket)
    except Exception:  # noqa: BLE001
        await hub.disconnect(websocket)
