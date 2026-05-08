"""Database engine + helpers shared by the web app.

Uses SQLAlchemy Core so the same code works against both SQLite (local dev)
and Postgres (AWS RDS). For a fresh DB it bootstraps the schema by
delegating to the existing legacy module ``database.py`` when on SQLite, or
runs the equivalent statements directly via SQLAlchemy when on Postgres.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from server.settings import DATABASE_URL


def _make_engine() -> Engine:
    kwargs: dict[str, Any] = {"future": True, "pool_pre_ping": True}
    if DATABASE_URL.startswith("sqlite"):
        # FK enforcement + thread safety for SQLite
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(DATABASE_URL, **kwargs)


engine: Engine = _make_engine()


@contextmanager
def conn():
    """Yield a connection inside an implicit transaction; commit on success."""
    with engine.begin() as c:
        if DATABASE_URL.startswith("sqlite"):
            c.exec_driver_sql("PRAGMA foreign_keys = ON")
        yield c


def fetch_all(sql: str, params: dict | None = None) -> list[dict]:
    with conn() as c:
        result = c.execute(text(sql), params or {})
        return [dict(r._mapping) for r in result]


def fetch_one(sql: str, params: dict | None = None) -> dict | None:
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: dict | None = None) -> Any:
    with conn() as c:
        return c.execute(text(sql), params or {})


def init_schema() -> None:
    """Create tables if they don't exist.

    For SQLite we reuse the existing legacy ``database.py`` (it already does
    the right thing). For Postgres we translate the same DDL on the fly:
    INTEGER PRIMARY KEY AUTOINCREMENT -> SERIAL PRIMARY KEY, REAL -> NUMERIC,
    drop the SQLite-only PRAGMA. Keeps the schema in one place.
    """
    if DATABASE_URL.startswith("sqlite"):
        # Reuse the legacy schema definition module
        import database as legacy
        legacy.init_database()
        return

    # Postgres path -- translate from the legacy SQLite DDL.
    import database as legacy
    with conn() as c:
        for stmt in legacy.SCHEMA_STATEMENTS:
            translated = (stmt
                          .replace("INTEGER PRIMARY KEY AUTOINCREMENT",
                                   "SERIAL PRIMARY KEY")
                          .replace("REAL", "NUMERIC"))
            c.execute(text(translated))
        for stmt in legacy.INDEX_STATEMENTS:
            c.execute(text(stmt))
