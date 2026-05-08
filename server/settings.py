"""Runtime configuration. Reads from environment variables.

Environment variables (with defaults for local dev):
    DATABASE_URL  - SQLAlchemy URL. Defaults to SQLite at data/projects.db.
                    On AWS use:  postgresql+psycopg2://user:pwd@host:5432/dbname
    SECRET_KEY    - cookie signing key. MUST be set in production.
    DEBUG         - 'true'/'false', enables Jinja autoreload + uvicorn debug.
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SQLITE = f"sqlite:///{(DATA_DIR / 'projects.db').as_posix()}"

DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_SQLITE)
SECRET_KEY   = os.environ.get("SECRET_KEY") or (
    # Stable fallback for local dev so sessions survive restarts.
    # In production SECRET_KEY MUST be set via env var.
    "dev-only-key-change-me-in-production-" + secrets.token_hex(8)
)
DEBUG = os.environ.get("DEBUG", "false").lower() in ("1", "true", "yes")
SESSION_COOKIE_NAME = "rh_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days
