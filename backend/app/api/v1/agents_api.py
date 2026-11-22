"""AI agent profiles, investigation listings, and workflow triggers."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.deps import CurrentUser, DbSession
from app.models.incident import AIInvestigation, AgentExecution, AgentName
from app.services import secrets as secret_store
from app.services import investigation_service

router = APIRouter(prefix="/agents", tags=["agents"])

AGENT_PROFILES = [
    {
        "name": AgentName.monitoring.value,
        "title": "Monitoring Agent",
        "description": "Receives network events and ML alerts, routes cases for investigation.",
    },
    {
        "name": AgentName.investigation.value,
        "title": "Threat Investigation Agent",
        "description": "Examines evidence from ML predictions, Zeek/PCAP features, and connection patterns.",
    },
    {
        "name": AgentName.decision.value,
        "title": "Decision-Making Agent",
        "description": "Assigns severity and recommends allowlisted defensive actions.",
    },
    {
        "name": AgentName.response.value,
        "title": "Response Agent",
        "description": "Prepares allowlisted actions for approval; execution verified in Response Center.",
    },
    {
        "name": AgentName.explanation.value,
        "title": "Explanation & Reporting Agent",
        "description": "Produces plain-language summaries from real evidence only.",
    },
]


class InvestigationOut(BaseModel):
    id: int
    incident_id: int
    status: str
    severity: str
    summary: str
    explanation: str
    recommended_action: str
    used_openai: bool
    error_message: str
    uncertainty_notes: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentExecutionOut(BaseModel):
    id: int
    investigation_id: Optional[int]
    agent_name: str
    status: str
    error_message: str
    duration_ms: int
    output_json: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}


class InvestigateRequest(BaseModel):
    prediction_id: Optional[int] = None
    incident_id: Optional[int] = None


class BatchInvestigateRequest(BaseModel):
    limit: int = Field(default=5, ge=1, le=25)


@router.get("/profiles")
def agent_profiles(_: CurrentUser):
    ai = secret_store.openai_status()
    return {
        "ai_configured": ai["configured"],
        "ai_status": ai["status"],
        "agents": [
            {
                **profile,
                "status": "ready" if ai["configured"] else "rule_based_fallback",
            }
            for profile in AGENT_PROFILES
        ],
        "message": (
            None
            if ai["configured"]
            else "OpenAI API key is not configured. Please visit Settings → AI Configuration "
            "to enable AI-powered investigations. Rule-based agents still run on confirmed evidence."
        ),
    }


@router.get("/investigations", response_model=list[InvestigationOut])
def list_investigations(_: CurrentUser, db: DbSession, limit: int = Query(50, ge=1, le=200)):
    return (
        db.query(AIInvestigation)
        .order_by(AIInvestigation.id.desc())
        .limit(limit)
        .all()
    )


@router.get("/investigations/{investigation_id}", response_model=InvestigationOut)
def get_investigation(_: CurrentUser, investigation_id: int, db: DbSession):
    row = db.query(AIInvestigation).filter(AIInvestigation.id == investigation_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return row


@router.get("/investigations/{investigation_id}/detail")
def investigation_detail(_: CurrentUser, investigation_id: int, db: DbSession):
    """Full investigation detail for Intelligence page — joined from real DB rows."""
    import json

    from app.models.incident import ResponseRecommendation, SecurityIncident
    from app.models.ml import Prediction
    from app.models.network import NetworkEvent, TrafficRecord

    inv = db.query(AIInvestigation).filter(AIInvestigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    incident = db.query(SecurityIncident).filter(SecurityIncident.id == inv.incident_id).first()
    prediction = None
    event = None
    traffic = None
    if incident and incident.prediction_id:
        prediction = db.query(Prediction).filter(Prediction.id == incident.prediction_id).first()
    if incident and incident.network_event_id:
        event = db.query(NetworkEvent).filter(NetworkEvent.id == incident.network_event_id).first()
    if prediction and prediction.traffic_record_id:
        traffic = db.query(TrafficRecord).filter(TrafficRecord.id == prediction.traffic_record_id).first()
    if prediction and prediction.network_event_id and not event:
        event = db.query(NetworkEvent).filter(NetworkEvent.id == prediction.network_event_id).first()

    executions = (
        db.query(AgentExecution)
        .filter(AgentExecution.investigation_id == inv.id)
        .order_by(AgentExecution.id.asc())
        .all()
    )
    recommendations = (
        db.query(ResponseRecommendation)
        .filter(ResponseRecommendation.investigation_id == inv.id)
        .order_by(ResponseRecommendation.id.desc())
        .all()
    )

    evidence = {}
    try:
        evidence = json.loads(inv.evidence_json or "{}")
    except json.JSONDecodeError:
        evidence = {}

    uncertainties = []
    try:
        raw_u = json.loads(inv.uncertainty_notes or "[]")
        if isinstance(raw_u, list):
            uncertainties = raw_u
        elif raw_u:
            uncertainties = [raw_u]
    except json.JSONDecodeError:
        if inv.uncertainty_notes:
            uncertainties = [inv.uncertainty_notes]

    pred_evidence = {}
    if prediction:
        try:
            pred_evidence = json.loads(prediction.evidence_json or "{}")
        except json.JSONDecodeError:
            pred_evidence = {}

    started = inv.created_at
    completed = executions[-1].created_at if executions else inv.updated_at if hasattr(inv, "updated_at") else inv.created_at

    ai = secret_store.openai_status()
    return {
        "investigation": {
            "id": inv.id,
            "incident_id": inv.incident_id,
            "status": inv.status.value if hasattr(inv.status, "value") else str(inv.status),
            "severity": inv.severity.value if hasattr(inv.severity, "value") else str(inv.severity),
            "summary": inv.summary,
            "explanation": inv.explanation,
            "recommended_action": inv.recommended_action,
            "used_openai": inv.used_openai,
            "error_message": inv.error_message,
            "uncertainty_notes": uncertainties,
            "evidence": evidence,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
            "completed_at": completed.isoformat() if completed else None,
        },
        "incident": (
            {
                "id": incident.id,
                "title": incident.title,
                "description": incident.description,
                "severity": incident.severity.value if hasattr(incident.severity, "value") else str(incident.severity),
                "status": incident.status.value if hasattr(incident.status, "value") else str(incident.status),
                "source_ip": incident.source_ip,
                "dest_ip": incident.dest_ip,
                "attack_category": incident.attack_category,
                "prediction_id": incident.prediction_id,
                "network_event_id": incident.network_event_id,
            }
            if incident
            else None
        ),
        "prediction": (
            {
                "id": prediction.id,
                "predicted_label": prediction.predicted_label,
                "attack_category": prediction.attack_category,
                "confidence": prediction.confidence,
                "severity": prediction.severity,
                "anomaly_score": prediction.anomaly_score,
                "evidence": pred_evidence,
                "created_at": prediction.created_at.isoformat() if prediction.created_at else None,
            }
            if prediction
            else None
        ),
        "network_event": (
            {
                "id": event.id,
                "event_type": event.event_type,
                "source_ip": event.source_ip,
                "dest_ip": event.dest_ip,
                "source_port": event.source_port,
                "dest_port": event.dest_port,
                "protocol": event.protocol,
                "summary": event.summary,
                "is_suspicious": event.is_suspicious,
                "is_demo": event.is_demo,
            }
            if event
            else None
        ),
        "traffic_record": (
            {
                "id": traffic.id,
                "source_ip": traffic.source_ip,
                "dest_ip": traffic.dest_ip,
                "source_port": traffic.source_port,
                "dest_port": traffic.dest_port,
                "protocol": traffic.protocol,
                "packet_count": traffic.packet_count,
                "bytes_transferred": traffic.bytes_transferred,
                "duration": traffic.duration,
                "connection_state": traffic.connection_state,
                "tcp_flags": traffic.tcp_flags,
                "label": traffic.label.value if hasattr(traffic.label, "value") else str(traffic.label),
            }
            if traffic
            else None
        ),
        "agent_executions": [
            {
                "id": e.id,
                "agent_name": e.agent_name.value if hasattr(e.agent_name, "value") else str(e.agent_name),
                "status": e.status,
                "error_message": e.error_message,
                "duration_ms": e.duration_ms,
                "output_json": e.output_json,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in executions
        ],
        "recommendations": [
            {
                "id": r.id,
                "action_type": r.action_type.value if hasattr(r.action_type, "value") else str(r.action_type),
                "rationale": r.rationale,
                "approval_status": (
                    r.approval_status.value if hasattr(r.approval_status, "value") else str(r.approval_status)
                ),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in recommendations
        ],
        "ai_configured": ai["configured"],
        "ai_message": (
            None
            if ai["configured"]
            else "OpenAI API key is not configured. ML evidence and rule-based investigation results are shown. "
            "Visit Settings → AI Configuration to enable LLM narratives."
        ),
    }


@router.get("/intelligence/overview")
def intelligence_overview(_: CurrentUser, db: DbSession):
    """Aggregates for the Intelligence hub — counts only from real investigation/incident rows."""
    from collections import Counter

    from app.models.incident import InvestigationStatus, SecurityIncident

    invs = db.query(AIInvestigation).all()
    executions = db.query(AgentExecution).order_by(AgentExecution.id.desc()).limit(200).all()

    sev_counts = Counter(
        (i.severity.value if hasattr(i.severity, "value") else str(i.severity)) for i in invs
    )
    status_counts = Counter(
        (i.status.value if hasattr(i.status, "value") else str(i.status)) for i in invs
    )
    import json

    cat_counts: Counter[str] = Counter()
    incident_map = {
        inc.id: inc
        for inc in db.query(SecurityIncident)
        .filter(SecurityIncident.id.in_([i.incident_id for i in invs] or [-1]))
        .all()
    }
    for i in invs:
        cat = ""
        try:
            ev = json.loads(i.evidence_json or "{}")
            cat = str(ev.get("attack_category") or "")
        except Exception:  # noqa: BLE001
            cat = ""
        if not cat:
            inc = incident_map.get(i.incident_id)
            cat = (inc.attack_category if inc else "") or ""
        if cat:
            cat_counts[cat] += 1

    confirmed = sum(
        1
        for i in invs
        if (i.status.value if hasattr(i.status, "value") else str(i.status))
        in (InvestigationStatus.completed.value, "completed")
    )
    failed = sum(
        1
        for i in invs
        if (i.status.value if hasattr(i.status, "value") else str(i.status))
        in (InvestigationStatus.failed.value, "failed")
    )
    pending = sum(
        1
        for i in invs
        if (i.status.value if hasattr(i.status, "value") else str(i.status))
        in (
            InvestigationStatus.pending.value,
            InvestigationStatus.running.value,
            "pending",
            "running",
        )
    )

    agent_latest: dict = {}
    for e in executions:
        name = e.agent_name.value if hasattr(e.agent_name, "value") else str(e.agent_name)
        if name not in agent_latest:
            agent_latest[name] = {
                "agent_name": name,
                "status": e.status,
                "error_message": e.error_message,
                "duration_ms": e.duration_ms,
                "investigation_id": e.investigation_id,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "output_preview": (e.output_json or "")[:180],
            }

    ai = secret_store.openai_status()
    return {
        "totals": {
            "investigations": len(invs),
            "critical": sev_counts.get("critical", 0),
            "high": sev_counts.get("high", 0),
            "medium": sev_counts.get("medium", 0),
            "low": sev_counts.get("low", 0) + sev_counts.get("informational", 0),
            "awaiting": pending,
            "confirmed": confirmed,
            "failed": failed,
            "unconfirmed": max(len(invs) - confirmed - failed, 0),
        },
        "severity_distribution": [{"name": k, "value": v} for k, v in sev_counts.most_common()],
        "status_distribution": [{"name": k, "value": v} for k, v in status_counts.most_common()],
        "category_distribution": [{"name": k, "value": v} for k, v in cat_counts.most_common(12)],
        "agent_latest": [agent_latest.get(p["name"]) or {"agent_name": p["name"], "status": "idle"} for p in AGENT_PROFILES],
        "recent": [
            {
                "id": i.id,
                "incident_id": i.incident_id,
                "status": i.status.value if hasattr(i.status, "value") else str(i.status),
                "severity": i.severity.value if hasattr(i.severity, "value") else str(i.severity),
                "summary": i.summary,
                "used_openai": i.used_openai,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in sorted(invs, key=lambda x: x.id, reverse=True)[:12]
        ],
        "ai_configured": ai["configured"],
        "ai_message": (
            None
            if ai["configured"]
            else "OpenAI API key is not configured. Intelligence shows ML and rule-based investigation data. "
            "Configure a key under Settings → AI Configuration for LLM explanations."
        ),
    }


@router.get("/investigations/{investigation_id}/executions", response_model=list[AgentExecutionOut])
def investigation_executions(_: CurrentUser, investigation_id: int, db: DbSession):
    return (
        db.query(AgentExecution)
        .filter(AgentExecution.investigation_id == investigation_id)
        .order_by(AgentExecution.id.asc())
        .all()
    )


@router.get("/executions", response_model=list[AgentExecutionOut])
def list_executions(_: CurrentUser, db: DbSession, limit: int = Query(50, ge=1, le=200)):
    return (
        db.query(AgentExecution)
        .order_by(AgentExecution.id.desc())
        .limit(limit)
        .all()
    )


@router.post("/investigate")
def investigate(payload: InvestigateRequest, user: CurrentUser, db: DbSession):
    if payload.prediction_id is None and payload.incident_id is None:
        raise HTTPException(status_code=400, detail="prediction_id or incident_id is required")
    try:
        return investigation_service.run_investigation(
            db,
            prediction_id=payload.prediction_id,
            incident_id=payload.incident_id,
            user_id=user.id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Investigation failed: {exc}") from exc


@router.post("/investigate/batch")
def investigate_batch(payload: BatchInvestigateRequest, user: CurrentUser, db: DbSession):
    return investigation_service.investigate_top_attacks(
        db, limit=payload.limit, user_id=user.id
    )
