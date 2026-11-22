"""Read-only analytics aggregates from real DB rows — no synthetic series."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_

from app.core.deps import CurrentUser, DbSession
from app.models.incident import (
    AIInvestigation,
    ApprovalStatus,
    InvestigationStatus,
    ResponseRecommendation,
    SecurityIncident,
)
from app.models.ml import MLModel, Prediction, TrainingRun
from app.models.network import NetworkEvent, TrafficRecord

router = APIRouter(prefix="/analytics", tags=["analytics"])

RANGE_MAP = {
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
}


def _parse_range(
    range_key: str,
    start: Optional[str],
    end: Optional[str],
) -> tuple[datetime, datetime, str]:
    now = datetime.now(timezone.utc)
    if range_key == "custom":
        if not start or not end:
            raise HTTPException(
                status_code=400, detail="custom range requires start and end ISO timestamps"
            )
        try:
            s = datetime.fromisoformat(start.replace("Z", "+00:00"))
            e = datetime.fromisoformat(end.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid datetime: {exc}") from exc
        if e < s:
            raise HTTPException(status_code=400, detail="end must be after start")
        return s, e, "custom"
    delta = RANGE_MAP.get(range_key)
    if not delta:
        raise HTTPException(status_code=400, detail="range must be 15m|1h|24h|7d|custom")
    return now - delta, now, range_key


def _bucket_size(span: timedelta) -> timedelta:
    seconds = span.total_seconds()
    if seconds <= 3600:
        return timedelta(minutes=5)
    if seconds <= 86400:
        return timedelta(hours=1)
    return timedelta(hours=6)


def _floor_dt(dt: datetime, step: timedelta) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    secs = int((dt - epoch).total_seconds())
    step_s = max(int(step.total_seconds()), 1)
    floored = secs - (secs % step_s)
    return epoch + timedelta(seconds=floored)


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _metric(run_val: Optional[float], metrics: dict[str, Any], key: str) -> Optional[float]:
    if run_val is not None:
        return float(run_val)
    raw = metrics.get(key)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


@router.get("/overview")
def analytics_overview(
    _: CurrentUser,
    db: DbSession,
    range: str = Query("24h", alias="range"),
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    t0, t1, range_key = _parse_range(range, start, end)
    step = _bucket_size(t1 - t0)

    events = (
        db.query(NetworkEvent)
        .filter(and_(NetworkEvent.created_at >= t0, NetworkEvent.created_at <= t1))
        .all()
    )
    traffic = (
        db.query(TrafficRecord)
        .filter(and_(TrafficRecord.created_at >= t0, TrafficRecord.created_at <= t1))
        .all()
    )
    preds = (
        db.query(Prediction)
        .filter(and_(Prediction.created_at >= t0, Prediction.created_at <= t1))
        .all()
    )
    incidents = (
        db.query(SecurityIncident)
        .filter(and_(SecurityIncident.created_at >= t0, SecurityIncident.created_at <= t1))
        .all()
    )

    event_buckets: dict[str, int] = defaultdict(int)
    attack_buckets: dict[str, int] = defaultdict(int)
    normal_buckets: dict[str, int] = defaultdict(int)
    heatmap: dict[str, int] = defaultdict(int)

    for ev in events:
        ts = _aware(ev.created_at)
        key = _floor_dt(ts, step).isoformat()
        event_buckets[key] += 1
        if ev.is_suspicious:
            attack_buckets[key] += 1
        else:
            normal_buckets[key] += 1
        heatmap[f"{ts.weekday()}-{ts.hour}"] += 1

    for tr in traffic:
        ts = _aware(tr.created_at)
        key = _floor_dt(ts, step).isoformat()
        event_buckets[key] += 1
        label = tr.label.value if hasattr(tr.label, "value") else str(tr.label)
        if label in ("attack", "suspicious"):
            attack_buckets[key] += 1
        elif label == "normal":
            normal_buckets[key] += 1
        heatmap[f"{ts.weekday()}-{ts.hour}"] += 1

    for p in preds:
        if p.predicted_label == "attack":
            ts = _aware(p.created_at)
            key = _floor_dt(ts, step).isoformat()
            attack_buckets[key] += 1

    all_keys = sorted(set(event_buckets) | set(attack_buckets) | set(normal_buckets))
    time_series = [
        {
            "t": k,
            "events": event_buckets.get(k, 0),
            "normal": normal_buckets.get(k, 0),
            "malicious": attack_buckets.get(k, 0),
        }
        for k in all_keys
    ]

    severity_counts = Counter((p.severity or "unknown") for p in preds)
    category_counts = Counter(
        (p.attack_category or p.predicted_label or "unknown")
        for p in preds
        if p.predicted_label == "attack"
    )
    protocol_counts = Counter((tr.protocol or "unknown").upper() for tr in traffic if tr.protocol)

    src_counter: Counter[str] = Counter()
    port_counter: Counter[int] = Counter()
    for tr in traffic:
        if tr.source_ip:
            src_counter[tr.source_ip] += 1
        if tr.dest_port:
            port_counter[int(tr.dest_port)] += 1
    for p in preds:
        try:
            evd = json.loads(p.evidence_json or "{}")
            if evd.get("source_ip"):
                src_counter[str(evd["source_ip"])] += 1
            if evd.get("dest_port"):
                port_counter[int(evd["dest_port"])] += 1
        except Exception:  # noqa: BLE001
            pass

    running_inv = (
        db.query(AIInvestigation)
        .filter(AIInvestigation.status == InvestigationStatus.running)
        .count()
    )
    all_inv = db.query(AIInvestigation).count()
    pending_resp = (
        db.query(ResponseRecommendation)
        .filter(ResponseRecommendation.approval_status == ApprovalStatus.pending)
        .count()
    )

    models = db.query(MLModel).order_by(MLModel.id.desc()).limit(20).all()
    model_perf: list[dict[str, Any]] = []
    for m in models:
        run = (
            db.query(TrainingRun)
            .filter(TrainingRun.model_id == m.id)
            .order_by(TrainingRun.id.desc())
            .first()
        )
        metrics: dict[str, Any] = {}
        if m.metrics_json:
            try:
                metrics = json.loads(m.metrics_json)
            except Exception:  # noqa: BLE001
                metrics = {}
        model_type = m.model_type.value if hasattr(m.model_type, "value") else str(m.model_type)
        model_perf.append(
            {
                "id": m.id,
                "name": m.name,
                "model_type": model_type,
                "is_active": m.is_active,
                "accuracy": _metric(run.accuracy if run else None, metrics, "accuracy"),
                "precision": _metric(run.precision if run else None, metrics, "precision"),
                "recall": _metric(run.recall if run else None, metrics, "recall"),
                "f1_score": _metric(run.f1_score if run else None, metrics, "f1_score"),
            }
        )

    detection_timeline = [
        {
            "id": p.id,
            "t": _aware(p.created_at).isoformat(),
            "label": p.predicted_label,
            "severity": p.severity,
            "category": p.attack_category,
            "confidence": p.confidence,
        }
        for p in sorted(preds, key=lambda x: x.created_at, reverse=True)[:40]
    ]

    incident_buckets: dict[str, int] = defaultdict(int)
    for inc in incidents:
        key = _floor_dt(_aware(inc.created_at), step).isoformat()
        incident_buckets[key] += 1

    return {
        "range": range_key,
        "start": t0.isoformat(),
        "end": t1.isoformat(),
        "bucket_seconds": int(step.total_seconds()),
        "counts": {
            "events": len(events),
            "traffic_flows": len(traffic),
            "predictions": len(preds),
            "attack_predictions": sum(1 for p in preds if p.predicted_label == "attack"),
            "incidents": len(incidents),
            "investigations_total": all_inv,
            "investigations_running": running_inv,
            "pending_responses": pending_resp,
        },
        "time_series": time_series,
        "incident_series": [{"t": k, "count": incident_buckets[k]} for k in sorted(incident_buckets)],
        "severity_distribution": [{"name": k, "value": v} for k, v in severity_counts.most_common()],
        "attack_categories": [{"name": k, "value": v} for k, v in category_counts.most_common(12)],
        "protocol_distribution": [{"name": k, "value": v} for k, v in protocol_counts.most_common()],
        "top_source_ips": [{"ip": ip, "count": c} for ip, c in src_counter.most_common(10)],
        "top_dest_ports": [{"port": p, "count": c} for p, c in port_counter.most_common(10)],
        "heatmap": [{"day": int(k.split("-")[0]), "hour": int(k.split("-")[1]), "count": v} for k, v in heatmap.items()],
        "detection_timeline": detection_timeline,
        "model_performance": model_perf,
        "has_heatmap_data": bool(heatmap),
        "has_time_series": bool(time_series),
    }
