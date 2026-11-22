"""PCAP upload, persistence, and processing pipeline."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.audit import AuditLog
from app.models.network import (
    MonitoringMode,
    NetworkEvent,
    PcapFile,
    PcapStatus,
    TrafficLabel,
    TrafficRecord,
)
from app.network.feature_extraction import (
    apply_aggregate_heuristics,
    extract_flows_from_pcap,
    heuristic_suspicious,
)
from app.network.pcap_validation import PcapValidationError, validate_pcap_bytes
from app.network.zeek_runner import run_zeek_on_pcap, zeek_available

logger = logging.getLogger(__name__)


def _pcap_dir() -> Path:
    path = Path(get_settings().pcap_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(
    db: Session,
    *,
    filename: str,
    data: bytes,
    user_id: Optional[int],
    is_demo: bool = False,
) -> PcapFile:
    fmt = validate_pcap_bytes(data, filename)
    digest = hashlib.sha256(data).hexdigest()

    existing = db.query(PcapFile).filter(PcapFile.sha256 == digest).first()
    if existing:
        return existing

    stored_name = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{Path(filename).name}"
    stored_path = _pcap_dir() / stored_name
    stored_path.write_bytes(data)

    record = PcapFile(
        original_filename=filename,
        stored_path=str(stored_path),
        file_size_bytes=len(data),
        sha256=digest,
        status=PcapStatus.uploaded,
        is_demo=is_demo,
        uploaded_by_id=user_id,
        error_message=f"format={fmt}",
    )
    db.add(record)
    db.add(
        AuditLog(
            actor_id=user_id,
            action="pcap.upload",
            resource_type="pcap",
            detail=f"Uploaded {filename} ({len(data)} bytes, demo={is_demo})",
            success=True,
        )
    )
    db.commit()
    db.refresh(record)
    try:
        from app.services.automation.pipeline import on_pcap_uploaded

        on_pcap_uploaded(db, pcap_id=record.id, user_id=user_id)
    except Exception:  # noqa: BLE001
        logger.exception("PCAP upload automation hook failed")
    return record


def process_pcap(db: Session, pcap_id: int, user_id: Optional[int] = None) -> dict:
    pcap = db.query(PcapFile).filter(PcapFile.id == pcap_id).first()
    if not pcap:
        raise FileNotFoundError("PCAP record not found")

    pcap.status = PcapStatus.processing
    pcap.error_message = ""
    db.commit()

    path = Path(pcap.stored_path)
    processed_dir = Path(get_settings().data_dir) / "processed" / f"pcap_{pcap.id}"
    processed_dir.mkdir(parents=True, exist_ok=True)

    try:
        zeek_result = run_zeek_on_pcap(path, processed_dir / "zeek")
        flows = extract_flows_from_pcap(path)

        # Clear previous derived rows if re-processing (events first — FK to traffic_records)
        db.query(NetworkEvent).filter(NetworkEvent.pcap_id == pcap.id).delete()
        db.query(TrafficRecord).filter(TrafficRecord.pcap_id == pcap.id).delete()
        db.flush()

        aggregate_reasons = apply_aggregate_heuristics(flows)
        suspicious_count = 0
        for idx, flow in enumerate(flows):
            is_susp, reason = heuristic_suspicious(flow)
            extra = aggregate_reasons.get(idx, "")
            if extra:
                is_susp = True
                reason = f"{reason}; {extra}".strip("; ").strip()
            if is_susp:
                suspicious_count += 1
            label = TrafficLabel.suspicious if is_susp else TrafficLabel.normal
            tr = TrafficRecord(
                pcap_id=pcap.id,
                source_ip=flow.source_ip,
                dest_ip=flow.dest_ip,
                source_port=flow.source_port,
                dest_port=flow.dest_port,
                protocol=flow.protocol,
                duration=flow.duration,
                packet_count=flow.packet_count,
                bytes_transferred=flow.bytes_transferred,
                connection_state=flow.connection_state,
                tcp_flags=flow.tcp_flags,
                label=label,
                raw_features_json=flow.to_dict()["raw_features_json"],
            )
            db.add(tr)
            db.flush()
            db.add(
                NetworkEvent(
                    pcap_id=pcap.id,
                    traffic_record_id=tr.id,
                    event_type="flow",
                    source_ip=flow.source_ip,
                    dest_ip=flow.dest_ip,
                    source_port=flow.source_port,
                    dest_port=flow.dest_port,
                    protocol=flow.protocol,
                    summary=reason or f"{flow.protocol} flow {flow.packet_count} pkts",
                    is_suspicious=is_susp,
                    is_demo=pcap.is_demo,
                    observed_at=datetime.now(timezone.utc),
                    monitoring_mode=MonitoringMode.offline,
                )
            )

        pcap.status = PcapStatus.processed
        pcap.error_message = ""
        db.add(
            AuditLog(
                actor_id=user_id,
                action="pcap.process",
                resource_type="pcap",
                resource_id=str(pcap.id),
                detail=f"flows={len(flows)} suspicious={suspicious_count} zeek={zeek_result.get('used')}",
                success=True,
            )
        )
        db.commit()

        automation = None
        try:
            from app.models.network import NetworkEvent as NE
            from app.services.automation.pipeline import on_network_events_created
            from app.services.ml_service import get_active_model, predict_pcap_flows

            event_ids = [e.id for e in db.query(NE).filter(NE.pcap_id == pcap.id).all()]
            on_network_events_created(db, event_ids=event_ids, user_id=user_id)
            # If an ML model is active, run predictions → auto incident/investigation pipeline
            if get_active_model(db):
                automation = predict_pcap_flows(db, pcap_id=pcap.id, limit=500, user_id=user_id)
        except Exception:  # noqa: BLE001
            logger.exception("Post-process automation skipped for pcap %s", pcap.id)

        return {
            "pcap_id": pcap.id,
            "status": pcap.status.value,
            "flows": len(flows),
            "suspicious_flows": suspicious_count,
            "extractor": "scapy",
            "zeek": zeek_result,
            "is_demo": pcap.is_demo,
            "monitoring_mode": "offline",
            "automation": automation,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("PCAP processing failed for id=%s", pcap_id)
        db.rollback()
        pcap = db.query(PcapFile).filter(PcapFile.id == pcap_id).first()
        if pcap:
            pcap.status = PcapStatus.failed
            pcap.error_message = str(exc)[:1000]
            db.add(
                AuditLog(
                    actor_id=user_id,
                    action="pcap.process",
                    resource_type="pcap",
                    resource_id=str(pcap.id),
                    detail="Processing failed",
                    success=False,
                )
            )
            db.commit()
        raise


def create_demo_pcap(db: Session, user_id: Optional[int]) -> PcapFile:
    """Generate a clearly labelled demo PCAP with mixed normal + scan-like traffic."""
    from scapy.all import IP, TCP, UDP, DNS, DNSQR, Ether, wrpcap  # type: ignore

    settings = get_settings()
    demo_path = Path(settings.pcap_dir) / "demo_offline_mixed_traffic.pcap"
    demo_path.parent.mkdir(parents=True, exist_ok=True)

    packets = []
    # Normal DNS + HTTP-ish TCP
    packets.append(Ether() / IP(src="10.0.0.10", dst="10.0.0.2") / UDP(sport=53000, dport=53) / DNS(rd=1, qd=DNSQR(qname="example.local")))
    packets.append(Ether() / IP(src="10.0.0.10", dst="10.0.0.20") / TCP(sport=51000, dport=80, flags="S"))
    packets.append(Ether() / IP(src="10.0.0.20", dst="10.0.0.10") / TCP(sport=80, dport=51000, flags="SA"))
    packets.append(Ether() / IP(src="10.0.0.10", dst="10.0.0.20") / TCP(sport=51000, dport=80, flags="A"))

    # SSH brute-ish SYNs
    for i in range(8):
        packets.append(
            Ether()
            / IP(src="10.0.0.66", dst="10.0.0.20")
            / TCP(sport=40000 + i, dport=22, flags="S")
        )

    # Quick high-rate SYN burst (DoS-ish demo pattern)
    for i in range(40):
        packets.append(
            Ether()
            / IP(src="10.0.0.99", dst="10.0.0.20")
            / TCP(sport=20000 + (i % 100), dport=80, flags="S")
        )

    wrpcap(str(demo_path), packets)
    data = demo_path.read_bytes()
    return save_upload(
        db,
        filename="demo_offline_mixed_traffic.pcap",
        data=data,
        user_id=user_id,
        is_demo=True,
    )


__all__ = [
    "PcapValidationError",
    "save_upload",
    "process_pcap",
    "create_demo_pcap",
    "zeek_available",
]
