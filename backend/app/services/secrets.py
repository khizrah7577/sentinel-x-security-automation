"""Encrypted secret storage for OpenAI API key (never returned in full)."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def _fernet() -> Fernet:
    settings = get_settings()
    key_path = Path(settings.secret_store_dir) / "fernet.key"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if not key_path.exists():
        # Derive a Fernet key from SECRET_KEY for persistence across restarts,
        # falling back to a generated key file if derivation fails.
        raw = settings.secret_key.encode("utf-8")
        padded = base64.urlsafe_b64encode((raw * 3)[:32])
        try:
            f = Fernet(padded)
            key_path.write_bytes(padded)
            return f
        except Exception:
            generated = Fernet.generate_key()
            key_path.write_bytes(generated)
            return Fernet(generated)
    return Fernet(key_path.read_bytes())


def _secret_file() -> Path:
    settings = get_settings()
    path = Path(settings.secret_store_dir) / "openai_secret.json.enc"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def save_openai_key(api_key: str, model: str) -> None:
    payload = json.dumps({"api_key": api_key, "model": model}).encode("utf-8")
    token = _fernet().encrypt(payload)
    _secret_file().write_bytes(token)


def load_openai_secrets() -> dict:
    path = _secret_file()
    if not path.exists():
        settings = get_settings()
        if settings.openai_api_key:
            return {"api_key": settings.openai_api_key, "model": settings.openai_model}
        return {}
    try:
        data = _fernet().decrypt(path.read_bytes())
        return json.loads(data.decode("utf-8"))
    except (InvalidToken, json.JSONDecodeError):
        return {}


def remove_openai_key() -> bool:
    path = _secret_file()
    if path.exists():
        path.unlink()
        return True
    return False


def mask_key(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:3]}...{api_key[-4:]}"


def openai_status() -> dict:
    secrets = load_openai_secrets()
    key = secrets.get("api_key", "")
    return {
        "configured": bool(key),
        "masked_key": mask_key(key) if key else "",
        "model": secrets.get("model") or get_settings().openai_model,
        "status": "configured" if key else "not_configured",
    }
