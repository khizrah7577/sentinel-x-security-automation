"""Health and readiness endpoints."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.database.session import check_database
from app.schemas.common import HealthResponse
from app.services import secrets as secret_store

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
@router.get("/api/v1/health", response_model=HealthResponse)
def health():
    settings = get_settings()
    db = check_database()
    ai = secret_store.openai_status()
    overall = "ok" if db.get("status") == "connected" else "degraded"
    return HealthResponse(
        status=overall,
        app=settings.app_name,
        env=settings.app_env,
        monitoring_mode=settings.monitoring_mode,
        ai_configured=ai["configured"],
        database=db,
        phase=11,
        response_mode=settings.response_mode,
    )
