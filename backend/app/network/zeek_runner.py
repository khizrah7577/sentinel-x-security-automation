"""Optional Zeek integration. Falls back gracefully when Zeek is unavailable."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def resolve_zeek_binary() -> Optional[str]:
    settings = get_settings()
    if settings.zeek_path and Path(settings.zeek_path).exists():
        return settings.zeek_path
    found = shutil.which("zeek") or shutil.which("bro")
    return found


def zeek_available() -> bool:
    settings = get_settings()
    if not settings.zeek_enabled and not settings.zeek_path:
        # Still report true if binary exists on PATH for status display
        return resolve_zeek_binary() is not None
    return resolve_zeek_binary() is not None


def run_zeek_on_pcap(pcap_path: Path, output_dir: Path) -> dict:
    """
    Attempt Zeek offline analysis.
    Returns structured result; does not raise when Zeek missing — caller uses Scapy.
    """
    binary = resolve_zeek_binary()
    if not binary:
        return {
            "used": False,
            "available": False,
            "message": "Zeek not installed/configured. Using Scapy feature extraction.",
            "conn_log": None,
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [binary, "-r", str(pcap_path), "local"],
            cwd=str(output_dir),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        conn_log = output_dir / "conn.log"
        return {
            "used": proc.returncode == 0 and conn_log.exists(),
            "available": True,
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "")[-2000:],
            "stderr": (proc.stderr or "")[-2000:],
            "conn_log": str(conn_log) if conn_log.exists() else None,
            "message": "Zeek completed" if proc.returncode == 0 else "Zeek failed; Scapy fallback used",
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Zeek execution error")
        return {
            "used": False,
            "available": True,
            "message": f"Zeek error: {exc}",
            "conn_log": None,
        }
