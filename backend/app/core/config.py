"""Application settings loaded from environment / .env (D: paths by default)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Host default (Windows FYP). Containers override with PROJECT_ROOT=/app.
_DEFAULT_ROOT = Path(os.environ.get("PROJECT_ROOT", r"D:\CyberSecurity_FYP"))
PROJECT_ROOT = _DEFAULT_ROOT


def _env_file_candidates() -> tuple[str, ...]:
    files: list[str] = []
    for candidate in (
        PROJECT_ROOT / ".env",
        Path("/app/.env"),
        Path(".env"),
    ):
        if candidate.is_file():
            files.append(str(candidate))
    return tuple(files) or (str(PROJECT_ROOT / ".env"),)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file_candidates(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SENTINEL X"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    secret_key: str = "change-me-to-a-long-random-string"
    access_token_expire_minutes: int = 60

    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / "data"
    pcap_dir: Path = PROJECT_ROOT / "data" / "pcaps"
    model_dir: Path = PROJECT_ROOT / "ml" / "saved_models"
    dataset_dir: Path = PROJECT_ROOT / "ml" / "datasets"
    log_dir: Path = PROJECT_ROOT / "logs"
    report_dir: Path = PROJECT_ROOT / "reports"
    secret_store_dir: Path = PROJECT_ROOT / "data" / "secrets"

    database_url: str = (
        "postgresql+psycopg://cybersec:cybersec_change_me@127.0.0.1:5432/cybersecurity_fyp"
    )

    frontend_origin: str = "http://127.0.0.1:5173"
    # Comma-separated extra CORS origins (e.g. http://localhost,https://example.com)
    cors_origins: str = ""

    # OpenAI key is managed at runtime via Settings UI / encrypted secret store.
    # Env var is optional bootstrap only — never required for core app use.
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    zeek_enabled: bool = False
    zeek_path: str = ""
    wireshark_tshark_path: str = ""
    monitoring_mode: str = "offline"
    response_mode: str = "approval_required"
    # When true (Oracle Always Free), block heavy ML training; inference still works.
    cloud_lightweight: bool = False
    disable_heavy_ml_training: bool = False

    bootstrap_admin_email: str = "admin@localhost"
    bootstrap_admin_password: str = "ChangeMeAdmin123!"
    bootstrap_analyst_email: str = "analyst@localhost"
    bootstrap_analyst_password: str = "ChangeMeAnalyst123!"


@lru_cache
def get_settings() -> Settings:
    return Settings()
