"""Allowlisted defensive actions — no arbitrary shell / no LLM-generated commands."""

from __future__ import annotations

import ipaddress
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.incident import (
    FirewallRule,
    IncidentStatus,
    ResponseActionType,
    SecurityIncident,
)

logger = logging.getLogger(__name__)

# Lab-oriented private ranges preferred; public IPs rejected for blocking actions.
LAB_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
]

LOW_RISK_ACTIONS = {
    ResponseActionType.create_alert,
    ResponseActionType.request_further_investigation,
    ResponseActionType.mark_resolved,
}

DISRUPTIVE_ACTIONS = {
    ResponseActionType.recommend_block_ip,
    ResponseActionType.apply_temp_firewall_rule,
    ResponseActionType.remove_temp_firewall_rule,
}


class ActionError(ValueError):
    pass


def validate_lab_ip(ip_str: str) -> str:
    if not ip_str:
        raise ActionError("Target IP is required")
    try:
        addr = ipaddress.ip_address(ip_str.strip())
    except ValueError as exc:
        raise ActionError(f"Invalid IP address: {ip_str}") from exc
    if any(addr in net for net in LAB_NETWORKS):
        return str(addr)
    raise ActionError(
        f"IP {addr} is outside configured lab private ranges. "
        "Blocking public/third-party addresses is not allowed in this prototype."
    )


def parse_params(raw: str | dict | None) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def execute_allowlisted_action(
    db: Session,
    *,
    action_type: ResponseActionType,
    parameters: dict[str, Any],
    incident: Optional[SecurityIncident],
    user_id: Optional[int],
) -> dict[str, Any]:
    """
    Execute one allowlisted action in the simulated lab.
    Returns execution metadata including verification + rollback flags.
    """
    if action_type == ResponseActionType.create_alert:
        detail = f"Alert created for incident #{incident.id if incident else 'n/a'}"
        return {
            "success": True,
            "verification_result": detail,
            "rollback_available": False,
            "parameters": parameters,
            "artifact": {"alert": detail},
        }

    if action_type == ResponseActionType.request_further_investigation:
        if incident:
            incident.status = IncidentStatus.investigating
        return {
            "success": True,
            "verification_result": "Incident marked for further investigation",
            "rollback_available": False,
            "parameters": parameters,
            "artifact": {},
        }

    if action_type == ResponseActionType.mark_resolved:
        if incident:
            incident.status = IncidentStatus.resolved
            incident.resolved_at = datetime.now(timezone.utc)
        return {
            "success": True,
            "verification_result": f"Incident #{incident.id if incident else '?'} marked resolved",
            "rollback_available": True,
            "parameters": parameters,
            "artifact": {"previous_status": "awaiting_approval"},
        }

    if action_type in {
        ResponseActionType.recommend_block_ip,
        ResponseActionType.apply_temp_firewall_rule,
    }:
        target = validate_lab_ip(str(parameters.get("target_ip") or ""))
        expires = datetime.now(timezone.utc) + timedelta(hours=int(parameters.get("ttl_hours") or 1))
        rule = FirewallRule(
            target_ip=target,
            direction=str(parameters.get("direction") or "inbound"),
            action="block",
            is_temporary=True,
            is_active=True,
            expires_at=expires,
            lab_only=True,
            created_by_id=user_id,
            notes=(
                f"Simulated lab firewall rule for incident "
                f"#{incident.id if incident else 'n/a'} (not a host OS firewall change)."
            ),
        )
        db.add(rule)
        db.flush()
        # Verification: rule exists and is active
        verified = (
            db.query(FirewallRule)
            .filter(FirewallRule.id == rule.id, FirewallRule.is_active.is_(True))
            .first()
            is not None
        )
        return {
            "success": verified,
            "verification_result": (
                f"Lab firewall rule #{rule.id} active for {target}"
                if verified
                else "Rule insert verification failed"
            ),
            "rollback_available": True,
            "parameters": {**parameters, "target_ip": target, "firewall_rule_id": rule.id},
            "artifact": {"firewall_rule_id": rule.id},
        }

    if action_type == ResponseActionType.remove_temp_firewall_rule:
        rule_id = parameters.get("firewall_rule_id")
        target = parameters.get("target_ip")
        q = db.query(FirewallRule).filter(FirewallRule.is_active.is_(True))
        if rule_id:
            q = q.filter(FirewallRule.id == int(rule_id))
        elif target:
            q = q.filter(FirewallRule.target_ip == validate_lab_ip(str(target)))
        else:
            raise ActionError("firewall_rule_id or target_ip required to remove a rule")
        rules = q.all()
        if not rules:
            raise ActionError("No active matching lab firewall rule found")
        ids = []
        for rule in rules:
            rule.is_active = False
            ids.append(rule.id)
        return {
            "success": True,
            "verification_result": f"Deactivated lab firewall rule(s): {ids}",
            "rollback_available": True,
            "parameters": {**parameters, "deactivated_rule_ids": ids},
            "artifact": {"deactivated_rule_ids": ids},
        }

    raise ActionError(f"Action not allowlisted: {action_type}")


def rollback_execution(
    db: Session,
    *,
    action_type: ResponseActionType,
    parameters: dict[str, Any],
    incident: Optional[SecurityIncident],
) -> dict[str, Any]:
    if action_type == ResponseActionType.mark_resolved and incident:
        incident.status = IncidentStatus.awaiting_approval
        incident.resolved_at = None
        return {"success": True, "verification_result": "Incident reopened (rollback)"}

    if action_type in {
        ResponseActionType.recommend_block_ip,
        ResponseActionType.apply_temp_firewall_rule,
    }:
        rule_id = parameters.get("firewall_rule_id")
        if not rule_id:
            raise ActionError("No firewall_rule_id stored for rollback")
        rule = db.query(FirewallRule).filter(FirewallRule.id == int(rule_id)).first()
        if not rule:
            raise ActionError("Firewall rule not found for rollback")
        rule.is_active = False
        return {
            "success": True,
            "verification_result": f"Rolled back lab firewall rule #{rule.id} (deactivated)",
        }

    if action_type == ResponseActionType.remove_temp_firewall_rule:
        ids = parameters.get("deactivated_rule_ids") or []
        restored = []
        for rid in ids:
            rule = db.query(FirewallRule).filter(FirewallRule.id == int(rid)).first()
            if rule:
                rule.is_active = True
                restored.append(rule.id)
        return {
            "success": True,
            "verification_result": f"Restored lab firewall rule(s): {restored}",
        }

    raise ActionError(f"Rollback not supported for action {action_type.value}")
