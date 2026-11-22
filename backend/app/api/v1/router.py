"""Aggregate API v1 routers."""

from fastapi import APIRouter

from app.api.v1 import (
    agents_api,
    ai_settings,
    analytics_api,
    auth,
    automation_api,
    dashboard,
    incidents,
    ml_api,
    network,
    reports_api,
    response_api,
    users,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(dashboard.router)
api_router.include_router(ai_settings.router)
api_router.include_router(network.router)
api_router.include_router(analytics_api.router)
api_router.include_router(incidents.router)
api_router.include_router(ml_api.router)
api_router.include_router(agents_api.router)
api_router.include_router(response_api.router)
api_router.include_router(reports_api.router)
api_router.include_router(automation_api.router)
