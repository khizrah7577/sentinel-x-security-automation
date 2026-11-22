"""Five specialized agent nodes. Evidence-bound; no invented network facts."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.agents.llm import AINotConfigured, ai_available, llm_json
from app.agents.state import AgentState, EvidencePack

logger = logging.getLogger(__name__)

ALLOWLISTED_ACTIONS = [
    "create_alert",
    "recommend_block_ip",
    "apply_temp_firewall_rule",
    "remove_temp_firewall_rule",
    "mark_resolved",
    "request_further_investigation",
]


def _trace(state: AgentState, agent: str, status: str, payload: dict[str, Any], started: float) -> None:
    state.setdefault("agent_trace", []).append(
        {
            "agent": agent,
            "status": status,
            "output": payload,
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }
    )


def _evidence_text(evidence: EvidencePack) -> str:
    return json.dumps(evidence, indent=2, default=str)


def _rule_severity(evidence: EvidencePack) -> str:
    conf = float(evidence.get("ml_confidence") or 0)
    label = (evidence.get("ml_label") or "").lower()
    port = int(evidence.get("dest_port") or 0)
    if label in {"attack", "suspicious"} and conf >= 0.9:
        return "critical" if port in {22, 3389} else "high"
    if label in {"attack", "suspicious"} and conf >= 0.7:
        return "high"
    if label in {"attack", "suspicious"}:
        return "medium"
    return "low"


def _rule_action(severity: str, evidence: EvidencePack) -> str:
    if severity in {"critical", "high"}:
        return "recommend_block_ip"
    if severity == "medium":
        return "create_alert"
    if severity == "low":
        return "request_further_investigation"
    return "mark_resolved"


def monitoring_agent(state: AgentState) -> AgentState:
    started = time.perf_counter()
    evidence = state.get("evidence") or {}
    missing = list(evidence.get("missing_evidence") or [])
    if not evidence.get("source_ip"):
        missing.append("source_ip")
    if not evidence.get("dest_ip"):
        missing.append("dest_ip")

    needs = bool(
        (evidence.get("ml_label") or "").lower() in {"attack", "suspicious"}
        or float(evidence.get("ml_confidence") or 0) >= 0.6
    )
    out = {
        "needs_investigation": needs,
        "priority": _rule_severity(evidence) if needs else "informational",
        "missing_evidence": missing,
        "facts_only": True,
        "notes": "Monitoring agent routed event using confirmed ML/network fields only.",
    }
    state["monitoring"] = out
    state["ai_enabled"] = ai_available()
    _trace(state, "monitoring", "completed", out, started)
    return state


def investigation_agent(state: AgentState) -> AgentState:
    started = time.perf_counter()
    evidence = state.get("evidence") or {}
    errors = state.setdefault("errors", [])

    rule_findings = {
        "confirmed_facts": {
            "source_ip": evidence.get("source_ip"),
            "dest_ip": evidence.get("dest_ip"),
            "dest_port": evidence.get("dest_port"),
            "protocol": evidence.get("protocol"),
            "ml_label": evidence.get("ml_label"),
            "ml_confidence": evidence.get("ml_confidence"),
            "event_summary": evidence.get("event_summary"),
            "is_demo": evidence.get("is_demo"),
        },
        "possible_explanations": [],
        "uncertainty": [],
        "missing_evidence": evidence.get("missing_evidence") or [],
        "pattern_match": [],
    }
    port = int(evidence.get("dest_port") or 0)
    if port == 22 and (evidence.get("ml_label") or "").lower() == "attack":
        rule_findings["possible_explanations"].append(
            "Observed destination port 22 with an attack ML label may indicate SSH probing/brute-force."
        )
        rule_findings["uncertainty"].append(
            "Credential success/failure is not present in the evidence pack."
        )
    if port == 80 and float(evidence.get("packet_count") or 0) <= 2:
        rule_findings["possible_explanations"].append(
            "Short TCP flows to port 80 can match SYN-scan or flood-like patterns."
        )
    if evidence.get("is_demo"):
        rule_findings["uncertainty"].append("Traffic is labelled as demo/offline capture.")

    used_ai = False
    ai_part: dict[str, Any] = {}
    if state.get("ai_enabled"):
        try:
            ai_part = llm_json(
                system=(
                    "You are a cybersecurity investigation agent. "
                    "Use ONLY the provided evidence JSON. "
                    "Never invent IPs, ports, packet counts, or logs. "
                    "Separate confirmed_facts from possible_explanations and uncertainty. "
                    "Return JSON with keys: confirmed_facts, possible_explanations, "
                    "uncertainty, missing_evidence, pattern_match."
                ),
                user=f"Evidence pack:\n{_evidence_text(evidence)}",
            )
            used_ai = True
            # Keep rule confirmed facts authoritative
            ai_part["confirmed_facts"] = rule_findings["confirmed_facts"]
        except AINotConfigured as exc:
            errors.append(str(exc))
            state["ai_enabled"] = False
        except Exception as exc:  # noqa: BLE001
            errors.append(f"investigation_llm_error: {exc}")
            logger.exception("Investigation LLM failed")

    out = {
        **rule_findings,
        "ai": ai_part if used_ai else None,
        "used_openai": used_ai,
    }
    state["investigation"] = out
    _trace(state, "investigation", "completed" if not errors else "completed_with_errors", out, started)
    return state


def decision_agent(state: AgentState) -> AgentState:
    started = time.perf_counter()
    evidence = state.get("evidence") or {}
    inv = state.get("investigation") or {}
    errors = state.setdefault("errors", [])

    severity = _rule_severity(evidence)
    action = _rule_action(severity, evidence)
    rationale = (
        f"Based on confirmed ML label '{evidence.get('ml_label')}' "
        f"(confidence={evidence.get('ml_confidence')}) and destination "
        f"{evidence.get('dest_ip')}:{evidence.get('dest_port')}."
    )

    used_ai = False
    ai_part: dict[str, Any] = {}
    if state.get("ai_enabled"):
        try:
            ai_part = llm_json(
                system=(
                    "You are a SOC decision agent. Choose severity from "
                    "[informational, low, medium, high, critical]. "
                    f"Recommend ONE allowlisted action from {ALLOWLISTED_ACTIONS}. "
                    "Use only provided evidence/investigation. Do not invent facts. "
                    "Return JSON: severity, recommended_action, rationale, uncertainty."
                ),
                user=(
                    f"Evidence:\n{_evidence_text(evidence)}\n\n"
                    f"Investigation:\n{json.dumps(inv, default=str)[:4000]}"
                ),
            )
            used_ai = True
            sev = str(ai_part.get("severity") or severity).lower()
            if sev in {"informational", "low", "medium", "high", "critical"}:
                severity = sev
            act = str(ai_part.get("recommended_action") or action)
            if act in ALLOWLISTED_ACTIONS:
                action = act
            if ai_part.get("rationale"):
                rationale = str(ai_part["rationale"])
        except AINotConfigured as exc:
            errors.append(str(exc))
            state["ai_enabled"] = False
        except Exception as exc:  # noqa: BLE001
            errors.append(f"decision_llm_error: {exc}")

    out = {
        "severity": severity,
        "recommended_action": action,
        "rationale": rationale,
        "allowlisted_only": True,
        "used_openai": used_ai,
        "ai": ai_part if used_ai else None,
        "uncertainty": (inv.get("uncertainty") or []) + list((ai_part or {}).get("uncertainty") or []),
    }
    state["decision"] = out
    _trace(state, "decision", "completed", out, started)
    return state


def response_agent(state: AgentState) -> AgentState:
    """Phase 7: prepare allowlisted response recommendation only (no execution)."""
    started = time.perf_counter()
    evidence = state.get("evidence") or {}
    decision = state.get("decision") or {}
    action = decision.get("recommended_action") or "create_alert"
    if action not in ALLOWLISTED_ACTIONS:
        action = "create_alert"

    out = {
        "action_type": action,
        "parameters": {
            "target_ip": evidence.get("source_ip"),
            "lab_only": True,
            "temporary": True,
        },
        "requires_approval": action
        in {"recommend_block_ip", "apply_temp_firewall_rule", "remove_temp_firewall_rule"},
        "execution_status": "pending_approval",
        "notes": (
            "Response agent prepared an allowlisted action. "
            "Execution/verification occurs after administrator approval (Phase 8)."
        ),
        "used_openai": False,
    }
    state["response_plan"] = out
    _trace(state, "response", "completed", out, started)
    return state


def explanation_agent(state: AgentState) -> AgentState:
    started = time.perf_counter()
    evidence = state.get("evidence") or {}
    decision = state.get("decision") or {}
    inv = state.get("investigation") or {}
    errors = state.setdefault("errors", [])

    facts = inv.get("confirmed_facts") or {}
    summary = (
        f"Event {evidence.get('source_ip')} → {evidence.get('dest_ip')}:{evidence.get('dest_port')} "
        f"({evidence.get('protocol')}) labelled {evidence.get('ml_label')} "
        f"by model with confidence {evidence.get('ml_confidence')}."
    )
    explanation = (
        f"{summary} Severity assessed as {decision.get('severity')}. "
        f"Recommended allowlisted action: {decision.get('recommended_action')}. "
        "Only confirmed evidence fields were used; missing telemetry is listed as uncertainty."
    )

    used_ai = False
    ai_part: dict[str, Any] = {}
    if state.get("ai_enabled"):
        try:
            ai_part = llm_json(
                system=(
                    "Explain the investigation in clear English for an administrator. "
                    "Do not invent network observations. Cite only provided facts. "
                    "Return JSON: summary, explanation, key_facts, uncertainties."
                ),
                user=(
                    f"Facts:\n{json.dumps(facts, default=str)}\n"
                    f"Decision:\n{json.dumps(decision, default=str)}\n"
                    f"Evidence:\n{_evidence_text(evidence)}"
                ),
            )
            used_ai = True
            if ai_part.get("summary"):
                summary = str(ai_part["summary"])
            if ai_part.get("explanation"):
                explanation = str(ai_part["explanation"])
        except AINotConfigured as exc:
            errors.append(str(exc))
            state["ai_enabled"] = False
        except Exception as exc:  # noqa: BLE001
            errors.append(f"explanation_llm_error: {exc}")

    out = {
        "summary": summary,
        "explanation": explanation,
        "key_facts": facts,
        "uncertainties": inv.get("uncertainty") or [],
        "used_openai": used_ai,
        "ai": ai_part if used_ai else None,
    }
    state["explanation"] = out
    _trace(state, "explanation", "completed", out, started)
    return state
