"""Automation workflows, schedules, notifications, and execution history."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class WorkflowTrigger(str, enum.Enum):
    new_network_event = "new_network_event"
    ml_attack_prediction = "ml_attack_prediction"
    critical_severity = "critical_severity"
    repeated_failed_login = "repeated_failed_login"
    pcap_uploaded = "pcap_uploaded"
    investigation_completed = "investigation_completed"
    response_approval = "response_approval"
    scheduled_task = "scheduled_task"


class WorkflowActionType(str, enum.Enum):
    create_incident = "create_incident"
    start_investigation = "start_investigation"
    generate_report = "generate_report"
    send_notification = "send_notification"
    create_response_recommendation = "create_response_recommendation"
    request_approval = "request_approval"
    execute_approved_action = "execute_approved_action"


class AutomationWorkflow(Base, TimestampMixin):
    __tablename__ = "automation_workflows"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    trigger: Mapped[WorkflowTrigger] = mapped_column(Enum(WorkflowTrigger, name="workflow_trigger"))
    conditions_json: Mapped[str] = mapped_column(Text, default="[]")
    actions_json: Mapped[str] = mapped_column(Text, default="[]")
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str] = mapped_column(String(64), default="")
    run_count: Mapped[int] = mapped_column(Integer, default=0)


class WorkflowExecution(Base, TimestampMixin):
    __tablename__ = "workflow_executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[Optional[int]] = mapped_column(ForeignKey("automation_workflows.id"), index=True)
    trigger: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(64), default="completed", index=True)
    context_json: Mapped[str] = mapped_column(Text, default="{}")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)


class ScheduledTaskKind(str, enum.Enum):
    system_health = "system_health"
    daily_security_summary = "daily_security_summary"
    review_pending_investigations = "review_pending_investigations"
    check_failed_agent_executions = "check_failed_agent_executions"
    weekly_ml_performance = "weekly_ml_performance"
    cleanup_expired_firewall_rules = "cleanup_expired_firewall_rules"


class ScheduledTask(Base, TimestampMixin):
    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[ScheduledTaskKind] = mapped_column(Enum(ScheduledTaskKind, name="scheduled_task_kind"))
    cron_or_interval: Mapped[str] = mapped_column(String(128), default="interval:300")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str] = mapped_column(String(64), default="")
    last_error: Mapped[str] = mapped_column(Text, default="")
    is_running: Mapped[bool] = mapped_column(Boolean, default=False)


class ScheduledTaskRun(Base, TimestampMixin):
    __tablename__ = "scheduled_task_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("scheduled_tasks.id"), index=True)
    status: Mapped[str] = mapped_column(String(64), default="completed")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)


class NotificationSeverity(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"
    success = "success"


class AppNotification(Base, TimestampMixin):
    __tablename__ = "app_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(64), default="general", index=True)
    severity: Mapped[NotificationSeverity] = mapped_column(
        Enum(NotificationSeverity, name="notification_severity"),
        default=NotificationSeverity.info,
    )
    link: Mapped[str] = mapped_column(String(512), default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    meta_json: Mapped[str] = mapped_column(Text, default="{}")


class NotificationRule(Base, TimestampMixin):
    __tablename__ = "notification_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    event_type: Mapped[str] = mapped_column(String(64), default="critical_threat")
    min_severity: Mapped[str] = mapped_column(String(32), default="high")
    notify_admins: Mapped[bool] = mapped_column(Boolean, default=True)
    conditions_json: Mapped[str] = mapped_column(Text, default="{}")


class ResponseAutomationPolicy(Base, TimestampMixin):
    __tablename__ = "response_automation_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # Only LOW_RISK allowlisted actions may auto-run when allow_auto=True
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    require_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_auto: Mapped[bool] = mapped_column(Boolean, default=False)
    min_confidence: Mapped[float] = mapped_column(Float, default=0.9)
    min_severity: Mapped[str] = mapped_column(String(32), default="high")
    lab_only: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class AutomationDedupe(Base, TimestampMixin):
    """Prevent duplicate auto-incidents / investigations for the same prediction/event."""

    __tablename__ = "automation_dedupe"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(64), default="")
    reference_id: Mapped[str] = mapped_column(String(64), default="")
