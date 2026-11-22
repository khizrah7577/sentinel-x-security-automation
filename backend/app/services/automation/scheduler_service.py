"""APScheduler-backed recurring automation tasks with overlap prevention."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.automation import ScheduledTask, ScheduledTaskKind, ScheduledTaskRun
from app.models.incident import AIInvestigation, FirewallRule, InvestigationStatus
from app.models.ml import MLModel, Prediction
from app.models.network import NetworkEvent
from app.services.automation.notifications import create_notification

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


def _parse_interval(spec: str) -> int:
    # Formats: "interval:300" (seconds) or bare integer seconds
    raw = (spec or "interval:300").strip()
    if raw.startswith("interval:"):
        raw = raw.split(":", 1)[1]
    try:
        return max(30, int(raw))
    except ValueError:
        return 300


def _run_kind(db: Session, kind: ScheduledTaskKind) -> dict:
    if kind == ScheduledTaskKind.system_health:
        from app.database.session import check_database

        db_status = check_database()
        ok = db_status.get("status") == "connected"
        create_notification(
            db,
            title="System health check",
            body=f"Database: {db_status.get('status')}",
            category="health",
            severity="success" if ok else "warning",
            link="/settings",
            notify_admins=True,
            meta=db_status,
        )
        return {"database": db_status}

    if kind == ScheduledTaskKind.daily_security_summary:
        summary = {
            "events": db.query(NetworkEvent).count(),
            "predictions": db.query(Prediction).count(),
            "investigations": db.query(AIInvestigation).count(),
            "models": db.query(MLModel).count(),
        }
        create_notification(
            db,
            title="Daily security summary",
            body=(
                f"Events={summary['events']} · Predictions={summary['predictions']} · "
                f"Investigations={summary['investigations']} · Models={summary['models']}"
            ),
            category="summary",
            severity="info",
            link="/reports",
            notify_admins=True,
            meta=summary,
        )
        return summary

    if kind == ScheduledTaskKind.review_pending_investigations:
        pending = (
            db.query(AIInvestigation)
            .filter(AIInvestigation.status.in_([InvestigationStatus.pending, InvestigationStatus.running]))
            .count()
        )
        if pending:
            create_notification(
                db,
                title="Pending investigations",
                body=f"{pending} investigation(s) still pending/running.",
                category="investigation",
                severity="warning",
                link="/intelligence",
                notify_admins=True,
            )
        return {"pending": pending}

    if kind == ScheduledTaskKind.check_failed_agent_executions:
        from app.models.incident import AgentExecution

        failed = (
            db.query(AgentExecution)
            .filter(AgentExecution.status == "failed")
            .order_by(AgentExecution.id.desc())
            .limit(20)
            .all()
        )
        if failed:
            create_notification(
                db,
                title="Failed agent executions",
                body=f"{len(failed)} recent failed agent execution(s).",
                category="agent_failure",
                severity="warning",
                link="/agents",
                notify_admins=True,
            )
        return {"failed": len(failed)}

    if kind == ScheduledTaskKind.weekly_ml_performance:
        models = db.query(MLModel).order_by(MLModel.id.desc()).limit(5).all()
        lines = []
        for m in models:
            try:
                metrics = json.loads(m.metrics_json or "{}")
                f1 = metrics.get("f1_score")
                lines.append(f"{m.name}: F1={f1}")
            except Exception:  # noqa: BLE001
                lines.append(m.name)
        create_notification(
            db,
            title="Weekly ML performance",
            body="; ".join(lines) or "No models trained yet.",
            category="ml",
            severity="info",
            link="/models",
            notify_admins=True,
        )
        return {"models": len(models)}

    if kind == ScheduledTaskKind.cleanup_expired_firewall_rules:
        now = datetime.now(timezone.utc)
        expired = (
            db.query(FirewallRule)
            .filter(FirewallRule.is_active.is_(True), FirewallRule.expires_at.isnot(None), FirewallRule.expires_at < now)
            .all()
        )
        for rule in expired:
            rule.is_active = False
        db.commit()
        if expired:
            create_notification(
                db,
                title="Expired firewall rules cleaned",
                body=f"Deactivated {len(expired)} temporary lab firewall rule(s).",
                category="response",
                severity="info",
                link="/response",
                notify_admins=True,
            )
        return {"deactivated": len(expired)}

    return {"detail": "unknown_kind"}


def execute_task(task_id: int) -> None:
    db = SessionLocal()
    try:
        task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task or not task.enabled:
            return
        if task.is_running:
            logger.info("Skip overlapping run for task %s", task_id)
            return
        task.is_running = True
        db.commit()
        started = time.perf_counter()
        status = "completed"
        error = ""
        result: dict = {}
        try:
            result = _run_kind(db, task.kind)
        except Exception as exc:  # noqa: BLE001
            status = "failed"
            error = str(exc)
            logger.exception("Scheduled task %s failed", task_id)
        duration = int((time.perf_counter() - started) * 1000)
        db.add(
            ScheduledTaskRun(
                task_id=task.id,
                status=status,
                result_json=json.dumps(result, default=str),
                error_message=error,
                duration_ms=duration,
            )
        )
        task.last_run_at = datetime.now(timezone.utc)
        task.last_status = status
        task.last_error = error
        task.is_running = False
        db.commit()
    finally:
        db.close()


def _job(task_id: int) -> None:
    execute_task(task_id)


def sync_scheduler_jobs(db: Session) -> None:
    global _scheduler
    if _scheduler is None:
        return
    # Remove existing automation jobs
    for job in list(_scheduler.get_jobs()):
        if str(job.id).startswith("task_"):
            job.remove()
    tasks = db.query(ScheduledTask).filter(ScheduledTask.enabled.is_(True)).all()
    for t in tasks:
        seconds = _parse_interval(t.cron_or_interval)
        _scheduler.add_job(
            _job,
            trigger=IntervalTrigger(seconds=seconds),
            id=f"task_{t.id}",
            args=[t.id],
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )


def start_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.start()
    db = SessionLocal()
    try:
        seed_default_tasks(db)
        sync_scheduler_jobs(db)
    finally:
        db.close()
    logger.info("Automation scheduler started")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def seed_default_tasks(db: Session) -> None:
    defaults = [
        ("System health check", ScheduledTaskKind.system_health, "interval:300"),
        ("Daily security summary", ScheduledTaskKind.daily_security_summary, "interval:86400"),
        ("Review pending investigations", ScheduledTaskKind.review_pending_investigations, "interval:900"),
        ("Check failed agent executions", ScheduledTaskKind.check_failed_agent_executions, "interval:900"),
        ("Weekly ML performance", ScheduledTaskKind.weekly_ml_performance, "interval:604800"),
        ("Cleanup expired firewall rules", ScheduledTaskKind.cleanup_expired_firewall_rules, "interval:600"),
    ]
    for name, kind, interval in defaults:
        exists = db.query(ScheduledTask).filter(ScheduledTask.kind == kind).first()
        if exists:
            continue
        db.add(
            ScheduledTask(
                name=name,
                kind=kind,
                cron_or_interval=interval,
                enabled=True,
            )
        )
    db.commit()


def seed_default_workflows(db: Session) -> None:
    from app.models.automation import (
        AutomationWorkflow,
        NotificationRule,
        ResponseAutomationPolicy,
        WorkflowTrigger,
    )

    if db.query(AutomationWorkflow).count() == 0:
        db.add(
            AutomationWorkflow(
                name="High/Critical ML attack → investigate",
                description="When ML predicts an attack with high/critical severity, create incident and investigate.",
                enabled=True,
                trigger=WorkflowTrigger.ml_attack_prediction,
                conditions_json=json.dumps(
                    [
                        {"field": "severity", "op": "gte", "value": "high"},
                        {"field": "ml_confidence", "op": "gte", "value": 0.75},
                    ]
                ),
                actions_json=json.dumps(
                    [
                        {"type": "create_incident"},
                        {"type": "start_investigation"},
                        {
                            "type": "send_notification",
                            "title": "Automated investigation triggered",
                            "severity": "warning",
                            "link": "/intelligence",
                        },
                    ]
                ),
            )
        )
        db.add(
            AutomationWorkflow(
                name="Critical severity alert",
                description="Notify admins on critical severity detections.",
                enabled=True,
                trigger=WorkflowTrigger.critical_severity,
                conditions_json=json.dumps([{"field": "severity", "op": "eq", "value": "critical"}]),
                actions_json=json.dumps(
                    [
                        {
                            "type": "send_notification",
                            "title": "Critical threat detected",
                            "severity": "critical",
                            "link": "/detections",
                        }
                    ]
                ),
            )
        )

    if db.query(ResponseAutomationPolicy).count() == 0:
        db.add(
            ResponseAutomationPolicy(
                name="Auto create security alert (low-risk)",
                enabled=True,
                action_type="create_alert",
                require_approval=False,
                allow_auto=True,
                min_confidence=0.85,
                min_severity="high",
                lab_only=True,
                notes="Low-risk only. Never blocks IPs automatically.",
            )
        )
        db.add(
            ResponseAutomationPolicy(
                name="Recommend lab IP block (approval required)",
                enabled=True,
                action_type="recommend_block_ip",
                require_approval=True,
                allow_auto=False,
                min_confidence=0.95,
                min_severity="critical",
                lab_only=True,
                notes="Disruptive. Requires admin approval. Lab IPs only.",
            )
        )

    if db.query(NotificationRule).count() == 0:
        for name, event in [
            ("Critical threats", "critical_threat"),
            ("Investigations", "investigation"),
            ("Pending approvals", "approval"),
            ("Defensive action results", "response"),
            ("Scheduler / health", "health"),
        ]:
            db.add(
                NotificationRule(
                    name=name,
                    enabled=True,
                    event_type=event,
                    min_severity="info" if event in ("investigation", "health", "response") else "high",
                    notify_admins=True,
                )
            )

    db.commit()
