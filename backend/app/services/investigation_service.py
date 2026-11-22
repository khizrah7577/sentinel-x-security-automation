"""Create incidents and run the LangGraph investigation workflow."""

from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.agents.graph import run_investigation_workflow
from app.agents.llm import ai_available
from app.agents.state import AgentState, EvidencePack
from app.models.incident import (
    AIInvestigation,
    AgentExecution,
    AgentName,
    ApprovalStatus,
    IncidentStatus,
    InvestigationStatus,
    ResponseActionType,
    ResponseRecommendation,
    SecurityIncident,
    Severity,
)
from app.models.ml import Prediction
from app.models.network import NetworkEvent, TrafficRecord
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


def _sev(value: str) -> Severity:
    try:
        return Severity(value)
    except ValueError:
        return Severity.medium


def _action(value: str) -> ResponseActionType:
    try:
        return ResponseActionType(value)
    except ValueError:
        return ResponseActionType.create_alert


def build_evidence_from_prediction(db: Session, prediction_id: int) -> EvidencePack:
    pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not pred:
        raise FileNotFoundError("Prediction not found")

    event = None
    record = None
    if pred.network_event_id:
        event = db.query(NetworkEvent).filter(NetworkEvent.id == pred.network_event_id).first()
    if pred.traffic_record_id:
        record = db.query(TrafficRecord).filter(TrafficRecord.id == pred.traffic_record_id).first()

    evidence_json = {}
    try:
        evidence_json = json.loads(pred.evidence_json or "{}")
    except json.JSONDecodeError:
        evidence_json = {}

    missing = []
    if not (event or record):
        missing.append("flow_record")

    return EvidencePack(
        prediction_id=pred.id,
        network_event_id=event.id if event else None,
        source_ip=(event.source_ip if event else evidence_json.get("source_ip", "")) or "",
        dest_ip=(event.dest_ip if event else evidence_json.get("dest_ip", "")) or "",
        source_port=int(event.source_port if event else evidence_json.get("source_port", 0) or 0),
        dest_port=int(event.dest_port if event else evidence_json.get("dest_port", 0) or 0),
        protocol=(event.protocol if event else evidence_json.get("protocol", "")) or "",
        packet_count=int(record.packet_count if record else evidence_json.get("packet_count", 0) or 0),
        bytes_transferred=int(
            record.bytes_transferred if record else evidence_json.get("bytes_transferred", 0) or 0
        ),
        duration=float(record.duration if record else 0.0),
        connection_state=(record.connection_state if record else ""),
        tcp_flags=(record.tcp_flags if record else ""),
        event_summary=(event.summary if event else ""),
        is_demo=bool(event.is_demo) if event else False,
        ml_label=pred.predicted_label,
        ml_confidence=float(pred.confidence or 0),
        ml_severity=pred.severity,
        ml_model=str(evidence_json.get("model") or pred.model_id or ""),
        attack_category=pred.attack_category,
        missing_evidence=missing,
    )


def ensure_incident_for_prediction(db: Session, prediction_id: int) -> SecurityIncident:
    existing = (
        db.query(SecurityIncident)
        .filter(SecurityIncident.prediction_id == prediction_id)
        .first()
    )
    if existing:
        return existing

    evidence = build_evidence_from_prediction(db, prediction_id)
    title = (
        f"ML {evidence.get('ml_label')} "
        f"{evidence.get('source_ip')} → {evidence.get('dest_ip')}:{evidence.get('dest_port')}"
    )
    incident = SecurityIncident(
        title=title[:255],
        description=evidence.get("event_summary") or "Created from ML prediction evidence.",
        severity=_sev(str(evidence.get("ml_severity") or "medium")),
        status=IncidentStatus.open,
        source_ip=str(evidence.get("source_ip") or ""),
        dest_ip=str(evidence.get("dest_ip") or ""),
        attack_category=str(evidence.get("attack_category") or ""),
        network_event_id=evidence.get("network_event_id"),
        prediction_id=prediction_id,
        is_demo=bool(evidence.get("is_demo")),
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def run_investigation(
    db: Session,
    *,
    prediction_id: Optional[int] = None,
    incident_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> dict:
    if prediction_id is not None:
        incident = ensure_incident_for_prediction(db, prediction_id)
        evidence = build_evidence_from_prediction(db, prediction_id)
    elif incident_id is not None:
        incident = db.query(SecurityIncident).filter(SecurityIncident.id == incident_id).first()
        if not incident:
            raise FileNotFoundError("Incident not found")
        if not incident.prediction_id:
            raise ValueError("Incident has no linked prediction/evidence to investigate")
        evidence = build_evidence_from_prediction(db, incident.prediction_id)
    else:
        raise ValueError("prediction_id or incident_id required")

    evidence["incident_id"] = incident.id
    incident.status = IncidentStatus.investigating

    inv = AIInvestigation(
        incident_id=incident.id,
        status=InvestigationStatus.running,
        used_openai=False,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    initial: AgentState = {
        "evidence": evidence,
        "ai_enabled": ai_available(),
        "errors": [],
        "agent_trace": [],
    }

    try:
        final = run_investigation_workflow(initial)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Workflow failed")
        inv.status = InvestigationStatus.failed
        inv.error_message = str(exc)[:1000]
        db.commit()
        raise

    decision = final.get("decision") or {}
    explanation = final.get("explanation") or {}
    response_plan = final.get("response_plan") or {}
    used_ai = any(
        bool((final.get(k) or {}).get("used_openai"))
        for k in ("investigation", "decision", "explanation")
    ) or bool(final.get("ai_enabled"))

    # Persist agent executions
    name_map = {
        "monitoring": AgentName.monitoring,
        "investigation": AgentName.investigation,
        "decision": AgentName.decision,
        "response": AgentName.response,
        "explanation": AgentName.explanation,
    }
    for step in final.get("agent_trace") or []:
        agent_key = step.get("agent")
        db.add(
            AgentExecution(
                investigation_id=inv.id,
                agent_name=name_map.get(agent_key, AgentName.investigation),
                status=step.get("status") or "completed",
                input_json=json.dumps({"evidence_keys": list(evidence.keys())}),
                output_json=json.dumps(step.get("output") or {}, default=str)[:20000],
                error_message="",
                duration_ms=int(step.get("duration_ms") or 0),
            )
        )

    severity = _sev(str(decision.get("severity") or "medium"))
    inv.status = (
        InvestigationStatus.completed
        if not (final.get("errors") and not explanation)
        else InvestigationStatus.completed
    )
    if not ai_available() and not used_ai:
        # Still completed via rule-based agents; mark clearly
        inv.error_message = (
            "OpenAI API key is not configured. Rule-based investigation completed. "
            "Visit Settings → AI Configuration to enable AI-powered reasoning."
        )
    inv.severity = severity
    inv.summary = str(explanation.get("summary") or "")[:5000]
    inv.explanation = str(explanation.get("explanation") or "")[:20000]
    inv.evidence_json = json.dumps(evidence, default=str)
    inv.recommended_action = str(decision.get("recommended_action") or "")
    inv.uncertainty_notes = json.dumps(
        (decision.get("uncertainty") or []) + (explanation.get("uncertainties") or []),
        default=str,
    )[:5000]
    inv.used_openai = bool(used_ai)

    incident.severity = severity
    incident.status = IncidentStatus.awaiting_approval
    incident.attack_category = str(evidence.get("attack_category") or incident.attack_category)

    action = _action(str(response_plan.get("action_type") or decision.get("recommended_action") or "create_alert"))
    rec = ResponseRecommendation(
        incident_id=incident.id,
        investigation_id=inv.id,
        action_type=action,
        parameters_json=json.dumps(response_plan.get("parameters") or {}, default=str),
        rationale=str(decision.get("rationale") or ""),
        approval_status=ApprovalStatus.pending,
    )
    db.add(rec)
    db.add(
        AuditLog(
            actor_id=user_id,
            action="ai.investigate",
            resource_type="investigation",
            resource_id=str(inv.id),
            detail=f"incident={incident.id} severity={severity.value} ai={used_ai}",
            success=True,
        )
    )
    db.commit()
    db.refresh(inv)
    db.refresh(incident)
    db.refresh(rec)

    auto_executed = None
    try:
        from app.services.response_service import maybe_auto_execute

        auto_executed = maybe_auto_execute(db, recommendation_id=rec.id)
        if auto_executed:
            db.refresh(rec)
    except Exception:  # noqa: BLE001
        logger.exception("Auto-execute skipped due to error")

    return {
        "investigation_id": inv.id,
        "incident_id": incident.id,
        "recommendation_id": rec.id,
        "status": inv.status.value,
        "severity": inv.severity.value,
        "summary": inv.summary,
        "explanation": inv.explanation,
        "recommended_action": inv.recommended_action,
        "used_openai": inv.used_openai,
        "ai_configured": ai_available(),
        "auto_executed_action_id": auto_executed.id if auto_executed else None,
        "errors": final.get("errors") or [],
        "agent_trace": final.get("agent_trace") or [],
        "message": (
            None
            if ai_available()
            else "OpenAI API key is not configured. Please visit Settings → AI Configuration "
            "to enable AI-powered investigations. A rule-based investigation was still completed."
        ),
    }


def investigate_top_attacks(db: Session, *, limit: int = 5, user_id: Optional[int] = None) -> dict:
    preds = (
        db.query(Prediction)
        .filter(Prediction.predicted_label == "attack")
        .order_by(Prediction.id.desc())
        .limit(limit)
        .all()
    )
    results = []
    for p in preds:
        try:
            results.append(run_investigation(db, prediction_id=p.id, user_id=user_id))
        except Exception as exc:  # noqa: BLE001
            results.append({"prediction_id": p.id, "error": str(exc)})
    return {"count": len(results), "results": results}
