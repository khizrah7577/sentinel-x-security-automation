"""Incidents, AI investigations, agent runs, and responses."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    pass


class Severity(str, enum.Enum):
    informational = "informational"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IncidentStatus(str, enum.Enum):
    open = "open"
    investigating = "investigating"
    awaiting_approval = "awaiting_approval"
    responding = "responding"
    resolved = "resolved"
    closed = "closed"


class InvestigationStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped_no_ai = "skipped_no_ai"


class AgentName(str, enum.Enum):
    monitoring = "monitoring"
    investigation = "investigation"
    decision = "decision"
    response = "response"
    explanation = "explanation"


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    auto_executed = "auto_executed"


class ResponseActionType(str, enum.Enum):
    create_alert = "create_alert"
    recommend_block_ip = "recommend_block_ip"
    apply_temp_firewall_rule = "apply_temp_firewall_rule"
    remove_temp_firewall_rule = "remove_temp_firewall_rule"
    mark_resolved = "mark_resolved"
    request_further_investigation = "request_further_investigation"


class SecurityIncident(Base, TimestampMixin):
    __tablename__ = "security_incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity"),
        default=Severity.informational,
        index=True,
    )
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, name="incident_status"),
        default=IncidentStatus.open,
        index=True,
    )
    source_ip: Mapped[str] = mapped_column(String(64), default="", index=True)
    dest_ip: Mapped[str] = mapped_column(String(64), default="")
    attack_category: Mapped[str] = mapped_column(String(128), default="")
    network_event_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("network_events.id"), nullable=True
    )
    prediction_id: Mapped[Optional[int]] = mapped_column(ForeignKey("predictions.id"), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    investigations: Mapped[list["AIInvestigation"]] = relationship(back_populates="incident")
    recommendations: Mapped[list["ResponseRecommendation"]] = relationship(
        back_populates="incident"
    )


class AIInvestigation(Base, TimestampMixin):
    __tablename__ = "ai_investigations"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("security_incidents.id"), index=True)
    status: Mapped[InvestigationStatus] = mapped_column(
        Enum(InvestigationStatus, name="investigation_status"),
        default=InvestigationStatus.pending,
    )
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="investigation_severity"),
        default=Severity.informational,
    )
    summary: Mapped[str] = mapped_column(Text, default="")
    explanation: Mapped[str] = mapped_column(Text, default="")
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    recommended_action: Mapped[str] = mapped_column(Text, default="")
    uncertainty_notes: Mapped[str] = mapped_column(Text, default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    used_openai: Mapped[bool] = mapped_column(Boolean, default=False)

    incident: Mapped[SecurityIncident] = relationship(back_populates="investigations")
    agent_executions: Mapped[list["AgentExecution"]] = relationship(
        back_populates="investigation"
    )


class AgentExecution(Base, TimestampMixin):
    __tablename__ = "agent_executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    investigation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ai_investigations.id"), index=True, nullable=True
    )
    agent_name: Mapped[AgentName] = mapped_column(Enum(AgentName, name="agent_name"))
    status: Mapped[str] = mapped_column(String(64), default="completed")
    input_json: Mapped[str] = mapped_column(Text, default="{}")
    output_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    investigation: Mapped[Optional[AIInvestigation]] = relationship(
        back_populates="agent_executions"
    )


class ResponseRecommendation(Base, TimestampMixin):
    __tablename__ = "response_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("security_incidents.id"), index=True)
    investigation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ai_investigations.id"), nullable=True
    )
    action_type: Mapped[ResponseActionType] = mapped_column(
        Enum(ResponseActionType, name="response_action_type")
    )
    parameters_json: Mapped[str] = mapped_column(Text, default="{}")
    rationale: Mapped[str] = mapped_column(Text, default="")
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status"),
        default=ApprovalStatus.pending,
        index=True,
    )
    approved_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str] = mapped_column(Text, default="")

    incident: Mapped[SecurityIncident] = relationship(back_populates="recommendations")
    executed_actions: Mapped[list["ExecutedAction"]] = relationship(
        back_populates="recommendation"
    )


class ExecutedAction(Base, TimestampMixin):
    __tablename__ = "executed_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    recommendation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("response_recommendations.id"), index=True
    )
    action_type: Mapped[ResponseActionType] = mapped_column(
        Enum(ResponseActionType, name="executed_action_type")
    )
    parameters_json: Mapped[str] = mapped_column(Text, default="{}")
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_result: Mapped[str] = mapped_column(Text, default="")
    rollback_available: Mapped[bool] = mapped_column(Boolean, default=False)
    rolled_back: Mapped[bool] = mapped_column(Boolean, default=False)
    executed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, default="")

    recommendation: Mapped[Optional[ResponseRecommendation]] = relationship(
        back_populates="executed_actions"
    )


class FirewallRule(Base, TimestampMixin):
    __tablename__ = "firewall_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_ip: Mapped[str] = mapped_column(String(64), index=True)
    direction: Mapped[str] = mapped_column(String(16), default="inbound")
    action: Mapped[str] = mapped_column(String(16), default="block")
    is_temporary: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    lab_only: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
