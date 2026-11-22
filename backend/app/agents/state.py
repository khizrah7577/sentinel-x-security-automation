"""Shared LangGraph state for the investigation workflow."""

from __future__ import annotations

from typing import Any, Optional, TypedDict


class EvidencePack(TypedDict, total=False):
    """Confirmed network/ML facts only — agents must not invent beyond this."""

    incident_id: int
    network_event_id: Optional[int]
    prediction_id: Optional[int]
    source_ip: str
    dest_ip: str
    source_port: int
    dest_port: int
    protocol: str
    packet_count: int
    bytes_transferred: int
    duration: float
    connection_state: str
    tcp_flags: str
    event_summary: str
    is_demo: bool
    ml_label: str
    ml_confidence: float
    ml_severity: str
    ml_model: str
    attack_category: str
    missing_evidence: list[str]


class AgentState(TypedDict, total=False):
    evidence: EvidencePack
    ai_enabled: bool
    errors: list[str]
    monitoring: dict[str, Any]
    investigation: dict[str, Any]
    decision: dict[str, Any]
    response_plan: dict[str, Any]
    explanation: dict[str, Any]
    agent_trace: list[dict[str, Any]]
