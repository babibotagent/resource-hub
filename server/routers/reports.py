"""Reports page — read-only aggregate views."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from server import security
from server.db import fetch_all

router = APIRouter()


@router.get("/reports", response_class=HTMLResponse)
def reports(request: Request):
    user = security.require_user(request)
    if user.get("role") not in ("admin", "project_manager"):
        from fastapi import HTTPException
        raise HTTPException(403, "Not authorized")

    hours_by_project = fetch_all("""
        SELECT p.project_code, p.project_name,
               COALESCE(SUM(te.hours), 0) AS total_hours,
               COUNT(te.time_entry_id) AS entries
        FROM "Project" p
        LEFT JOIN "Task" t ON t.project_id = p.project_id
        LEFT JOIN "Time_Entry" te ON te.task_id = t.task_id
        GROUP BY p.project_id, p.project_code, p.project_name
        ORDER BY total_hours DESC
    """)

    budget_vs_actual = fetch_all("""
        SELECT project_code, project_name,
               COALESCE(budget, 0) AS budget,
               COALESCE(actual_cost, 0) AS actual_cost,
               CASE WHEN budget > 0
                    THEN ROUND(100.0 * COALESCE(actual_cost,0) / budget, 1)
                    ELSE 0 END AS pct
        FROM "Project"
        ORDER BY pct DESC
    """)

    hours_by_person = fetch_all("""
        SELECT COALESCE(e.first_name || ' ' || e.last_name,
                        x.first_name || ' ' || x.last_name, 'Unassigned') AS person,
               COALESCE(SUM(te.hours), 0) AS total_hours,
               COUNT(te.time_entry_id) AS entries
        FROM "Time_Entry" te
        LEFT JOIN "Employee" e ON e.employee_id = te.employee_id
        LEFT JOIN "External_Resource" x ON x.external_id = te.external_id
        GROUP BY person
        ORDER BY total_hours DESC
    """)

    invoices_summary = fetch_all("""
        SELECT status,
               COUNT(*) AS cnt,
               COALESCE(SUM(total_amount), 0) AS total
        FROM "Invoice"
        GROUP BY status
        ORDER BY status
    """)

    return request.app.state.templates.TemplateResponse(request, name="reports.html", context={
        "request": request,
        "user": user,
        "active": "reports",
        "hours_by_project": hours_by_project,
        "budget_vs_actual": budget_vs_actual,
        "hours_by_person": hours_by_person,
        "invoices_summary": invoices_summary,
    })
