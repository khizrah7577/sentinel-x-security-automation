"""OpenAI client helper — uses runtime secret store only."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.services import secrets as secret_store

logger = logging.getLogger(__name__)


class AINotConfigured(RuntimeError):
    pass


def get_openai_client():
    secrets = secret_store.load_openai_secrets()
    key = secrets.get("api_key")
    if not key:
        raise AINotConfigured(
            "OpenAI API key is not configured. Please visit Settings → AI Configuration "
            "to enable AI-powered investigations."
        )
    from openai import OpenAI

    return OpenAI(api_key=key, timeout=45.0, max_retries=1), secrets.get("model") or "gpt-4o-mini"


def llm_json(
    *,
    system: str,
    user: str,
    temperature: float = 0.1,
) -> dict[str, Any]:
    """Call the LLM and parse a JSON object. Never returns fabricated evidence fields."""
    client, model = get_openai_client()
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    content = response.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
        if not isinstance(data, dict):
            return {"raw": content, "parse_error": "not_object"}
        return data
    except json.JSONDecodeError:
        return {"raw": content, "parse_error": "invalid_json"}


def ai_available() -> bool:
    return bool(secret_store.load_openai_secrets().get("api_key"))
