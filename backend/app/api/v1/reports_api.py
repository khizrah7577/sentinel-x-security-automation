"""Report listing / generation stubs using real DB aggregates."""

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
import csv
import io

from app.core.deps import CurrentUser, DbSession
from app.models.incident import SecurityIncident
from app.models.ml import MLModel, Prediction
from app.models.network import NetworkEvent

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary")
def report_summary(_: CurrentUser, db: DbSession):
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "network_events": db.query(NetworkEvent).count(),
        "incidents": db.query(SecurityIncident).count(),
        "predictions": db.query(Prediction).count(),
        "ml_models": db.query(MLModel).count(),
        "product": "SENTINEL X",
        "note": "SENTINEL X report statistics are taken from the live database; empty values mean no data ingested yet.",
    }


@router.get("/incidents.csv")
def incidents_csv(_: CurrentUser, db: DbSession):
    rows = db.query(SecurityIncident).order_by(SecurityIncident.id.desc()).limit(1000).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["id", "title", "severity", "status", "source_ip", "dest_ip", "attack_category", "is_demo", "created_at"]
    )
    for r in rows:
        writer.writerow(
            [
                r.id,
                r.title,
                r.severity.value if hasattr(r.severity, "value") else r.severity,
                r.status.value if hasattr(r.status, "value") else r.status,
                r.source_ip,
                r.dest_ip,
                r.attack_category,
                r.is_demo,
                r.created_at.isoformat() if r.created_at else "",
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=incidents_report.csv"},
    )


@router.get("/incidents.json")
def incidents_json(_: CurrentUser, db: DbSession):
    rows = db.query(SecurityIncident).order_by(SecurityIncident.id.desc()).limit(1000).all()
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "incidents": [
            {
                "id": r.id,
                "title": r.title,
                "severity": r.severity.value if hasattr(r.severity, "value") else r.severity,
                "status": r.status.value if hasattr(r.status, "value") else r.status,
                "source_ip": r.source_ip,
                "dest_ip": r.dest_ip,
                "attack_category": r.attack_category,
                "is_demo": r.is_demo,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }
    return JSONResponse(payload)
