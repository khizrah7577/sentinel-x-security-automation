"""Create tables and seed default users/settings."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.models import AppSetting, User  # noqa: F401 — register models
from app.models.user import UserRole

logger = logging.getLogger(__name__)


def init_db() -> None:
    # Ensure all models are imported
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_users(db)
        seed_settings(db)
        try:
            from app.services.automation.scheduler_service import (
                seed_default_tasks,
                seed_default_workflows,
            )

            seed_default_tasks(db)
            seed_default_workflows(db)
        except Exception:
            logger.exception("Automation seed skipped")
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Database bootstrap failed")
        raise
    finally:
        db.close()


def seed_users(db: Session) -> None:
    settings = get_settings()
    defaults = [
        (settings.bootstrap_admin_email, settings.bootstrap_admin_password, UserRole.admin, "Administrator"),
        (
            settings.bootstrap_analyst_email,
            settings.bootstrap_analyst_password,
            UserRole.analyst,
            "Analyst",
        ),
    ]
    for email, password, role, name in defaults:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            continue
        db.add(
            User(
                email=email,
                full_name=name,
                hashed_password=get_password_hash(password),
                role=role,
                is_active=True,
            )
        )
        logger.info("Seeded user %s (%s)", email, role.value)


def seed_settings(db: Session) -> None:
    defaults = {
        "response_mode": get_settings().response_mode,
        "monitoring_mode": get_settings().monitoring_mode,
        "theme_default": "system",
        "ai_last_tested_at": "",
        "ai_last_error": "",
    }
    for key, value in defaults.items():
        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        if not row:
            db.add(AppSetting(key=key, value=value, description=f"Default {key}"))
