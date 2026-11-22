"""Shared response schemas."""

from typing import Any, Optional

from pydantic import BaseModel


class Message(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    app: str
    env: str
    monitoring_mode: str
    ai_configured: bool
    database: dict[str, Any]
    phase: int
    response_mode: str


class AIConfigStatus(BaseModel):
    configured: bool
    masked_key: str = ""
    model: str
    status: str
    last_tested_at: Optional[str] = None
    last_error: Optional[str] = None


class AIConfigUpdate(BaseModel):
    api_key: str
    model: str = "gpt-4o-mini"


class DashboardStats(BaseModel):
    total_network_events: int = 0
    normal_traffic: int = 0
    suspicious_traffic: int = 0
    detected_attacks: int = 0
    critical_incidents: int = 0
    pending_approvals: int = 0
    ml_models: int = 0
    active_model: Optional[str] = None
    ai_configured: bool = False
    monitoring_mode: str = "offline"
