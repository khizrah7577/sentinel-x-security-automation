"""Application settings loaded from environment / .env (D: paths by default)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_project_root() -> Path:
    if "PROJECT_ROOT" in os.environ:
        return Path(os.environ["PROJECT_ROOT"])
    default_win = Path(r"D:\CyberSecurity_FYP")
    if default_win.is_dir():
        return default_win
    # Fallback to repo root based on this file's location (.../backend/app/core/config.py -> root)
    return Path(__file__).resolve().parent.parent.parent.parent


PROJECT_ROOT = _resolve_project_root()


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

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """Ensure SQLAlchemy psycopg3 driver prefix is used."""
        if not isinstance(v, str):
            return v
        v = v.strip()
        # Cloud platforms like Railway/Heroku provide postgres:// or postgresql://
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg://", 1)
        if v.startswith("postgresql://") and not v.startswith("postgresql+"):
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v

    def model_post_init(self, __context) -> None:
        """Ensure runtime directories exist safely without throwing errors."""
        for d in (
            self.data_dir,
            self.pcap_dir,
            self.model_dir,
            self.dataset_dir,
            self.log_dir,
            self.report_dir,
            self.secret_store_dir,
        ):
            try:
                d.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass


@lru_cache
def get_settings() -> Settings:
    return Settings()
