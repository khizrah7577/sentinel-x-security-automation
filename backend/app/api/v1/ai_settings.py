"""Runtime OpenAI API key configuration (admin only)."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from openai import OpenAI

from app.core.deps import AdminUser, DbSession
from app.models.audit import AuditLog
from app.models.user import AppSetting
from app.schemas.common import AIConfigStatus, AIConfigUpdate, Message
from app.services import secrets as secret_store

router = APIRouter(prefix="/settings/ai", tags=["settings-ai"])


def _get_setting(db: DbSession, key: str) -> str:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    return row.value if row else ""


def _set_setting(db: DbSession, key: str, value: str) -> None:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))


@router.get("", response_model=AIConfigStatus)
def get_ai_config(_: AdminUser, db: DbSession):
    status = secret_store.openai_status()
    return AIConfigStatus(
        configured=status["configured"],
        masked_key=status["masked_key"],
        model=status["model"],
        status=status["status"],
        last_tested_at=_get_setting(db, "ai_last_tested_at") or None,
        last_error=_get_setting(db, "ai_last_error") or None,
    )


@router.put("", response_model=AIConfigStatus)
def save_ai_config(payload: AIConfigUpdate, admin: AdminUser, db: DbSession):
    key = payload.api_key.strip()
    if not key or key.startswith("sk-") is False and len(key) < 20:
        # Allow non-sk keys too if long enough (project keys / alternate orgs)
        if len(key) < 20:
            raise HTTPException(status_code=400, detail="API key appears invalid")
    secret_store.save_openai_key(key, payload.model)
    _set_setting(db, "ai_last_error", "")
    db.add(
        AuditLog(
            actor_id=admin.id,
            action="ai_config.save",
            resource_type="openai",
            detail="API key saved (value not logged)",
            success=True,
        )
    )
    db.commit()
    status = secret_store.openai_status()
    return AIConfigStatus(
        configured=status["configured"],
        masked_key=status["masked_key"],
        model=status["model"],
        status="configured",
        last_tested_at=_get_setting(db, "ai_last_tested_at") or None,
        last_error=None,
    )


@router.post("/test", response_model=AIConfigStatus)
def test_ai_connection(admin: AdminUser, db: DbSession):
    secrets = secret_store.load_openai_secrets()
    key = secrets.get("api_key")
    model = secrets.get("model") or "gpt-4o-mini"
    if not key:
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key is not configured. Please visit Settings → AI Configuration.",
        )
    try:
        client = OpenAI(api_key=key)
        # Lightweight auth check — list models (does not invent network evidence)
        client.models.list()
        tested_at = datetime.now(timezone.utc).isoformat()
        _set_setting(db, "ai_last_tested_at", tested_at)
        _set_setting(db, "ai_last_error", "")
        db.add(
            AuditLog(
                actor_id=admin.id,
                action="ai_config.test",
                resource_type="openai",
                detail="Connection test succeeded",
                success=True,
            )
        )
        db.commit()
        status = secret_store.openai_status()
        return AIConfigStatus(
            configured=True,
            masked_key=status["masked_key"],
            model=model,
            status="connected",
            last_tested_at=tested_at,
            last_error=None,
        )
    except Exception as exc:  # noqa: BLE001
        err = str(exc)
        # Never include the key in error strings if SDK echoes it
        _set_setting(db, "ai_last_error", err[:500])
        db.add(
            AuditLog(
                actor_id=admin.id,
                action="ai_config.test",
                resource_type="openai",
                detail="Connection test failed",
                success=False,
            )
        )
        db.commit()
        raise HTTPException(status_code=400, detail=f"Connection test failed: {err[:300]}") from exc


@router.delete("", response_model=Message)
def remove_ai_config(admin: AdminUser, db: DbSession):
    secret_store.remove_openai_key()
    _set_setting(db, "ai_last_tested_at", "")
    _set_setting(db, "ai_last_error", "")
    db.add(
        AuditLog(
            actor_id=admin.id,
            action="ai_config.remove",
            resource_type="openai",
            detail="API key removed",
            success=True,
        )
    )
    db.commit()
    return Message(message="OpenAI API key removed")
