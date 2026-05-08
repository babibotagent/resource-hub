"""Dashboard route — KPI cards + a couple of summary tables."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from server import queries, security


router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    user = security.require_user(request)
    ctx = {
        "request": request,
        "user": user,
        "kpis": queries.dashboard_kpis(),
        "by_status": queries.projects_by_status(),
        "invoices_by_status": queries.invoices_by_status(),
        "top_projects": queries.top_projects_by_budget_usage(limit=5),
        "recent_risks": queries.recent_risks(limit=5),
        "active": "dashboard",
    }
    return request.app.state.templates.TemplateResponse("dashboard.html", ctx)
