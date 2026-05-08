"""FastAPI application entry point.

Run locally:
    uvicorn server.main:app --reload

Run in production (Docker / App Runner):
    uvicorn server.main:app --host 0.0.0.0 --port 8000

Environment variables:
    DATABASE_URL  - SQLAlchemy URL (defaults to local SQLite)
    SECRET_KEY    - cookie session key (REQUIRED in production)
    DEBUG         - 'true' enables Jinja autoreload
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from server import db, security
from server.routers import auth as auth_router
from server.routers import dashboard as dashboard_router
from server.routers import crud as crud_router
from server.routers import users as users_router
from server.routers import reports as reports_router
from server.settings import (
    DEBUG,
    SECRET_KEY,
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE,
    BASE_DIR,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("resourcehub")


app = FastAPI(title="ResourceHub", docs_url="/api/docs" if DEBUG else None)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie=SESSION_COOKIE_NAME,
    max_age=SESSION_MAX_AGE,
    same_site="lax",
    https_only=not DEBUG,
)

# Static files (CSS, logo, etc.)
STATIC_DIR = Path(BASE_DIR) / "server" / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Templates
templates = Jinja2Templates(directory=str(Path(BASE_DIR) / "server" / "templates"))
templates.env.auto_reload = DEBUG
app.state.templates = templates


@app.on_event("startup")
def _startup() -> None:
    db.init_schema()
    created = security.ensure_default_admin()
    if created:
        log.warning("Created default admin/admin user (must change at first login)")
    log.info("ResourceHub web ready")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    if security.current_user(request) is None:
        return RedirectResponse(url="/login", status_code=303)
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/healthz")
def healthz():
    """AWS App Runner health check endpoint."""
    return {"status": "ok"}


# Routers
app.include_router(auth_router.router)
app.include_router(dashboard_router.router)
app.include_router(users_router.router)
app.include_router(reports_router.router)
# CRUD router last — it has catch-all /{view_id} patterns
app.include_router(crud_router.router)
