"""Event-driven detection → incident → investigation automation pipeline."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.automation import AutomationDedupe, WorkflowTrigger
from app.models.ml import Prediction
from app.services.automation.notifications import create_notification
from app.services.automation.workflow_engine import evaluate_workflows
from app.services.investigation_service import ensure_incident_for_prediction, run_investigation

logger = logging.getLogger(__name__)

# Auto-create incidents / investigations only when severity/confidence meet policy
AUTO_SEVERITIES = {"high", "critical"}
AUTO_MIN_CONFIDENCE = 0.75


def _dedupe(db: Session, key: str, kind: str, reference_id: str) -> bool:
    """Return True if this key is NEW (claimed). False if already processed."""
    existing = db.query(AutomationDedupe).filter(AutomationDedupe.key == key).first()
    if existing:
        return False
    db.add(AutomationDedupe(key=key, kind=kind, reference_id=str(reference_id)))
    try:
        db.commit()
        return True
    except Exception:  # noqa: BLE001
        db.rollback()
        return False


def process_prediction_automation(
    db: Session,
    *,
    prediction_id: int,
    user_id: Optional[int] = None,
) -> dict:
    pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not pred:
        return {"ok": False, "error": "prediction_not_found"}

    ctx = {
        "prediction_id": pred.id,
        "predicted_label": pred.predicted_label,
        "attack_category": pred.attack_category,
        "severity": pred.severity,
        "confidence": pred.confidence,
        "ml_confidence": pred.confidence,
        "source_ip": "",
        "dest_ip": "",
        "dest_port": 0,
        "protocol": "",
        "summary": f"ML {pred.predicted_label} {pred.attack_category} conf={pred.confidence:.2f}",
    }
    try:
        import json

        ev = json.loads(pred.evidence_json or "{}")
        ctx["source_ip"] = str(ev.get("source_ip") or "")
        ctx["dest_ip"] = str(ev.get("dest_ip") or "")
        ctx["dest_port"] = int(ev.get("dest_port") or 0)
        ctx["protocol"] = str(ev.get("protocol") or "")
    except Exception:  # noqa: BLE001
        pass

    # Always evaluate workflows for ML attack predictions
    workflow_results = []
    if pred.predicted_label == "attack":
        workflow_results.extend(
            evaluate_workflows(
                db,
                trigger=WorkflowTrigger.ml_attack_prediction,
                context=ctx,
                user_id=user_id,
            )
        )
        if (pred.severity or "").lower() == "critical":
            workflow_results.extend(
                evaluate_workflows(
                    db,
                    trigger=WorkflowTrigger.critical_severity,
                    context=ctx,
                    user_id=user_id,
                )
            )

    auto = {"incident_id": None, "investigation_id": None, "skipped": False, "reason": ""}

    meets = (
        pred.predicted_label == "attack"
        and (pred.severity or "").lower() in AUTO_SEVERITIES
        and float(pred.confidence or 0) >= AUTO_MIN_CONFIDENCE
    )
    if not meets:
        auto["skipped"] = True
        auto["reason"] = "criteria_not_met"
        return {"ok": True, "auto": auto, "workflows": workflow_results}

    dedupe_key = f"pred_auto:{pred.id}"
    if not _dedupe(db, dedupe_key, "prediction_auto", str(pred.id)):
        auto["skipped"] = True
        auto["reason"] = "duplicate"
        return {"ok": True, "auto": auto, "workflows": workflow_results}

    try:
        incident = ensure_incident_for_prediction(db, pred.id)
        auto["incident_id"] = incident.id
        ctx["incident_id"] = incident.id

        create_notification(
            db,
            title=f"Threat detected: {pred.severity}",
            body=ctx["summary"],
            category="critical_threat" if pred.severity == "critical" else "threat",
            severity="critical" if pred.severity == "critical" else "warning",
            link="/intelligence",
            notify_admins=True,
            meta={"prediction_id": pred.id, "incident_id": incident.id},
        )

        # Start investigation (rule-based if no OpenAI key)
        inv_key = f"pred_inv:{pred.id}"
        if _dedupe(db, inv_key, "prediction_investigate", str(pred.id)):
            result = run_investigation(db, prediction_id=pred.id, user_id=user_id)
            auto["investigation_id"] = result.get("investigation_id")
            ctx["investigation_id"] = auto["investigation_id"]
            ai_note = ""
            if not result.get("ai_configured"):
                ai_note = " AI investigation unavailable (OpenAI key not configured); rule-based analysis stored."
                create_notification(
                    db,
                    title="AI investigation unavailable",
                    body=(
                        f"Investigation #{result.get('investigation_id')} completed with rule-based agents only. "
                        "Configure OpenAI in Settings to enable LangGraph AI reasoning."
                    ),
                    category="investigation",
                    severity="warning",
                    link="/settings",
                    notify_admins=True,
                    meta={"investigation_id": result.get("investigation_id"), "ai_status": "unavailable"},
                )
            create_notification(
                db,
                title="Investigation completed",
                body=(result.get("summary") or f"Investigation #{result.get('investigation_id')} created")
                + ai_note,
                category="investigation",
                severity="info",
                link="/intelligence",
                notify_admins=True,
                meta={
                    "investigation_id": result.get("investigation_id"),
                    "used_openai": result.get("used_openai"),
                    "ai_configured": result.get("ai_configured"),
                },
            )
            evaluate_workflows(
                db,
                trigger=WorkflowTrigger.investigation_completed,
                context={
                    **ctx,
                    "investigation_status": result.get("status"),
                    "investigation_id": result.get("investigation_id"),
                },
                user_id=user_id,
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Automation pipeline failed for prediction %s", prediction_id)
        create_notification(
            db,
            title="Investigation automation failed",
            body=str(exc),
            category="investigation_failure",
            severity="warning",
            link="/automation/history",
            notify_admins=True,
        )
        return {"ok": False, "error": str(exc), "auto": auto, "workflows": workflow_results}

    return {"ok": True, "auto": auto, "workflows": workflow_results}


def process_predictions_batch(
    db: Session,
    *,
    prediction_ids: list[int],
    user_id: Optional[int] = None,
) -> dict:
    outcomes = []
    for pid in prediction_ids:
        try:
            outcomes.append(process_prediction_automation(db, prediction_id=pid, user_id=user_id))
        except Exception as exc:  # noqa: BLE001
            outcomes.append({"ok": False, "prediction_id": pid, "error": str(exc)})
    return {"count": len(outcomes), "results": outcomes}


def on_pcap_uploaded(db: Session, *, pcap_id: int, user_id: Optional[int] = None) -> None:
    evaluate_workflows(
        db,
        trigger=WorkflowTrigger.pcap_uploaded,
        context={"pcap_id": pcap_id, "summary": f"PCAP #{pcap_id} uploaded"},
        user_id=user_id,
    )


def on_network_events_created(
    db: Session,
    *,
    event_ids: list[int],
    user_id: Optional[int] = None,
) -> None:
    for eid in event_ids[:50]:
        evaluate_workflows(
            db,
            trigger=WorkflowTrigger.new_network_event,
            context={"network_event_id": eid, "summary": f"Network event #{eid}"},
            user_id=user_id,
        )
