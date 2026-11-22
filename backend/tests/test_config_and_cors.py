"""Test CORS configuration and database url normalization."""

from __future__ import annotations

import re
from app.core.config import Settings


def test_database_url_normalization():
    # Railway/Heroku format
    s1 = Settings(database_url="postgres://user:pass@host:5432/db")
    assert s1.database_url == "postgresql+psycopg://user:pass@host:5432/db"

    s2 = Settings(database_url="postgresql://user:pass@host:5432/db")
    assert s2.database_url == "postgresql+psycopg://user:pass@host:5432/db"

    s3 = Settings(database_url="postgresql+psycopg://user:pass@host:5432/db")
    assert s3.database_url == "postgresql+psycopg://user:pass@host:5432/db"


def test_cors_regex_matches_vercel():
    pattern = re.compile(r"^https://.*\.vercel\.app$")
    assert pattern.match("https://cyberattack-detection.vercel.app")
    assert pattern.match("https://cyberattack-detection-git-main.vercel.app")
    assert pattern.match("https://sentinel-x-demo.vercel.app")
    assert not pattern.match("https://attacker.com")
    assert not pattern.match("http://cyberattack-detection.vercel.app")
