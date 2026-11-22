"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.services.bootstrap import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cybersecurity_fyp")
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        init_db()
        logger.info("Database initialized / seeded")
    except Exception:
        logger.exception(
            "Database init failed — API will start in degraded mode. "
            "Ensure Docker Postgres is running."
        )
    try:
        from app.services.automation.scheduler_service import start_scheduler

        start_scheduler()
    except Exception:
        logger.exception("Automation scheduler failed to start")
    yield
    try:
        from app.services.automation.scheduler_service import stop_scheduler

        stop_scheduler()
    except Exception:
        logger.exception("Automation scheduler shutdown error")


app = FastAPI(
    title=settings.app_name,
    description="Agentic AI cyber attack detection and response (academic prototype)",
    version="0.3.0",
    lifespan=lifespan,
)

_cors = [
    settings.frontend_origin,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]
if settings.cors_origins:
    _cors.extend([o.strip() for o in settings.cors_origins.split(",") if o.strip()])
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(_cors)),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(api_router)


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "docs": "/docs",
        "health": "/health",
        "phase": 3,
    }
