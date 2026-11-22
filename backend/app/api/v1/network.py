"""Network monitoring, PCAP upload, and offline analysis APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.models.network import NetworkEvent, PcapFile, TrafficRecord
from app.network.pcap_validation import MAX_PCAP_BYTES, PcapValidationError
from app.network.zeek_runner import zeek_available
from app.services import pcap_service

router = APIRouter(prefix="/network", tags=["network"])


class NetworkEventOut(BaseModel):
    id: int
    event_type: str
    source_ip: str
    dest_ip: str
    source_port: int
    dest_port: int
    protocol: str
    summary: str
    is_suspicious: bool
    is_demo: bool
    monitoring_mode: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PcapOut(BaseModel):
    id: int
    original_filename: str
    file_size_bytes: int
    sha256: str
    status: str
    is_demo: bool
    error_message: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TrafficOut(BaseModel):
    id: int
    pcap_id: Optional[int]
    source_ip: str
    dest_ip: str
    source_port: int
    dest_port: int
    protocol: str
    duration: float
    packet_count: int
    bytes_transferred: int
    connection_state: str
    tcp_flags: str
    label: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ProcessResult(BaseModel):
    pcap_id: int
    status: str
    flows: int
    suspicious_flows: int
    extractor: str
    zeek: dict
    is_demo: bool
    monitoring_mode: str


@router.get("/events", response_model=list[NetworkEventOut])
def list_events(
    _: CurrentUser,
    db: DbSession,
    suspicious: Optional[bool] = None,
    pcap_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=500),
):
    q = db.query(NetworkEvent).order_by(NetworkEvent.id.desc())
    if suspicious is not None:
        q = q.filter(NetworkEvent.is_suspicious.is_(suspicious))
    if pcap_id is not None:
        q = q.filter(NetworkEvent.pcap_id == pcap_id)
    return q.limit(limit).all()


@router.get("/pcaps", response_model=list[PcapOut])
def list_pcaps(_: CurrentUser, db: DbSession, limit: int = Query(50, ge=1, le=200)):
    return db.query(PcapFile).order_by(PcapFile.id.desc()).limit(limit).all()


@router.get("/pcaps/{pcap_id}", response_model=PcapOut)
def get_pcap(_: CurrentUser, pcap_id: int, db: DbSession):
    row = db.query(PcapFile).filter(PcapFile.id == pcap_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="PCAP not found")
    return row


@router.get("/pcaps/{pcap_id}/traffic", response_model=list[TrafficOut])
def pcap_traffic(
    _: CurrentUser,
    pcap_id: int,
    db: DbSession,
    limit: int = Query(200, ge=1, le=2000),
):
    return (
        db.query(TrafficRecord)
        .filter(TrafficRecord.pcap_id == pcap_id)
        .order_by(TrafficRecord.id.asc())
        .limit(limit)
        .all()
    )


@router.get("/status")
def monitoring_status(_: CurrentUser):
    settings = get_settings()
    zeek = zeek_available()
    return {
        "monitoring_mode": settings.monitoring_mode,
        "zeek_enabled": settings.zeek_enabled or zeek,
        "zeek_available": zeek,
        "live_capture_available": False,
        "max_upload_bytes": MAX_PCAP_BYTES,
        "extractor_primary": "zeek" if (settings.zeek_enabled and zeek) else "scapy",
        "message": (
            "Offline/PCAP mode active. Upload a PCAP for analysis. "
            + (
                "Zeek binary detected; offline Zeek runs will be attempted."
                if zeek
                else "Zeek not installed — Scapy feature extraction is used."
            )
        ),
    }


@router.post("/pcaps/upload", response_model=PcapOut)
async def upload_pcap(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    data = await file.read()
    try:
        record = pcap_service.save_upload(
            db,
            filename=file.filename,
            data=data,
            user_id=user.id,
            is_demo=False,
        )
        return record
    except PcapValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/pcaps/{pcap_id}/process", response_model=ProcessResult)
def process_pcap(pcap_id: int, user: CurrentUser, db: DbSession):
    try:
        return pcap_service.process_pcap(db, pcap_id=pcap_id, user_id=user.id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Processing failed: {exc}") from exc


@router.post("/pcaps/demo", response_model=PcapOut)
def create_demo(user: CurrentUser, db: DbSession):
    """Create a clearly labelled offline demo PCAP for FYP demonstration."""
    try:
        return pcap_service.create_demo_pcap(db, user_id=user.id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Demo PCAP creation failed: {exc}") from exc


@router.get("/stats")
def traffic_stats(_: CurrentUser, db: DbSession):
    from app.models.network import TrafficLabel
    from sqlalchemy import func

    total = db.query(TrafficRecord).count()
    normal = db.query(TrafficRecord).filter(TrafficRecord.label == TrafficLabel.normal).count()
    sus = db.query(TrafficRecord).filter(TrafficRecord.label == TrafficLabel.suspicious).count()
    attack = db.query(TrafficRecord).filter(TrafficRecord.label == TrafficLabel.attack).count()
    protocol_rows = (
        db.query(TrafficRecord.protocol, func.count(TrafficRecord.id))
        .group_by(TrafficRecord.protocol)
        .all()
    )
    protocols = { (row[0] or "UNKNOWN"): int(row[1]) for row in protocol_rows }
    return {
        "traffic_records": total,
        "normal": normal,
        "suspicious": sus,
        "attack": attack,
        "protocol_distribution": protocols,
        "pcap_files": db.query(PcapFile).count(),
        "network_events": db.query(NetworkEvent).count(),
    }


# Reference lab nodes matching demo PCAP / documented FYP lab IPs — not live GNS3.
LAB_REFERENCE_NODES = [
    {
        "id": "kali",
        "label": "Kali Attacker",
        "role": "attacker",
        "ips": ["10.0.0.66", "10.0.0.99"],
        "description": "Simulated attacker host used in labelled demo captures.",
    },
    {
        "id": "client",
        "label": "Ubuntu Client",
        "role": "client",
        "ips": ["10.0.0.10"],
        "description": "Simulated workstation / DNS client in the offline lab.",
    },
    {
        "id": "server",
        "label": "Ubuntu Server",
        "role": "server",
        "ips": ["10.0.0.20"],
        "description": "Simulated application/web server target.",
    },
    {
        "id": "dns",
        "label": "Lab DNS",
        "role": "infra",
        "ips": ["10.0.0.2"],
        "description": "Simulated DNS endpoint present in demo PCAP traffic.",
    },
    {
        "id": "monitor",
        "label": "Monitoring / SENTINEL X",
        "role": "monitor",
        "ips": ["10.0.0.1"],
        "description": "Reference monitoring/application host for the SOC platform.",
    },
]


@router.get("/lab-topology")
def lab_topology(_: CurrentUser, db: DbSession):
    """Simulated lab reference topology with observed traffic overlays from DB."""
    from collections import Counter, defaultdict
    from app.models.network import TrafficLabel

    ip_to_node: dict[str, str] = {}
    for node in LAB_REFERENCE_NODES:
        for ip in node["ips"]:
            ip_to_node[ip] = node["id"]

    traffic = db.query(TrafficRecord).all()
    events = db.query(NetworkEvent).all()

    edge_stats: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"count": 0, "suspicious": 0, "protocols": Counter(), "bytes": 0}
    )
    node_activity: dict[str, dict] = defaultdict(
        lambda: {"flow_count": 0, "suspicious": 0, "last_seen": None, "observed_ips": set()}
    )

    def touch_node(node_id: str, ip: str, suspicious: bool, when):
        st = node_activity[node_id]
        st["flow_count"] += 1
        if suspicious:
            st["suspicious"] += 1
        st["observed_ips"].add(ip)
        if when and (st["last_seen"] is None or when > st["last_seen"]):
            st["last_seen"] = when

    def add_edge(src_ip: str, dst_ip: str, protocol: str, suspicious: bool, bytes_: int, when):
        src_node = ip_to_node.get(src_ip)
        dst_node = ip_to_node.get(dst_ip)
        if not src_node or not dst_node or src_node == dst_node:
            return
        key = (src_node, dst_node)
        edge_stats[key]["count"] += 1
        if suspicious:
            edge_stats[key]["suspicious"] += 1
        if protocol:
            edge_stats[key]["protocols"][protocol.upper()] += 1
        edge_stats[key]["bytes"] += int(bytes_ or 0)
        touch_node(src_node, src_ip, suspicious, when)
        touch_node(dst_node, dst_ip, suspicious, when)

    for tr in traffic:
        label = tr.label.value if hasattr(tr.label, "value") else str(tr.label)
        suspicious = label in ("attack", "suspicious")
        add_edge(
            tr.source_ip,
            tr.dest_ip,
            tr.protocol,
            suspicious,
            tr.bytes_transferred,
            tr.created_at,
        )

    for ev in events:
        add_edge(
            ev.source_ip,
            ev.dest_ip,
            ev.protocol,
            bool(ev.is_suspicious),
            0,
            ev.created_at,
        )

    nodes_out = []
    for node in LAB_REFERENCE_NODES:
        act = node_activity.get(node["id"], {})
        nodes_out.append(
            {
                **node,
                "observed": bool(act.get("flow_count")),
                "flow_count": int(act.get("flow_count") or 0),
                "suspicious_count": int(act.get("suspicious") or 0),
                "last_seen": act["last_seen"].isoformat() if act.get("last_seen") else None,
                "observed_ips": sorted(act.get("observed_ips") or []),
            }
        )

    edges_out = []
    for (src, dst), st in edge_stats.items():
        top_proto = st["protocols"].most_common(1)
        edges_out.append(
            {
                "source": src,
                "target": dst,
                "count": st["count"],
                "suspicious_count": st["suspicious"],
                "bytes": st["bytes"],
                "top_protocol": top_proto[0][0] if top_proto else None,
                "observed": True,
            }
        )

    return {
        "mode": "simulated_lab_reference",
        "disclaimer": (
            "This is a simulated lab reference topology based on documented FYP/demo IPs. "
            "It is not a live GNS3 discovery feed. Edge/node activity reflects observed "
            "traffic and events stored in PostgreSQL."
        ),
        "nodes": nodes_out,
        "edges": edges_out,
        "observed_edge_count": len(edges_out),
        "total_traffic_records": len(traffic),
        "total_network_events": len(events),
    }
