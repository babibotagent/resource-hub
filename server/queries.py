"""Read-only aggregate queries used by the dashboard. Same shape as the
desktop ``queries.py`` but going through the SQLAlchemy engine so it works
on Postgres too. SQL is plain ANSI so it runs on both backends."""
from __future__ import annotations

from server.db import fetch_all, fetch_one


def dashboard_kpis() -> dict:
    out = {}
    out["employees"] = fetch_one(
        "SELECT COUNT(*) AS n FROM Employee WHERE status = 'active'")["n"]
    out["externals"] = fetch_one(
        "SELECT COUNT(*) AS n FROM External_Resource WHERE status = 'active'")["n"]
    out["customers"] = fetch_one(
        "SELECT COUNT(*) AS n FROM Customer WHERE status = 'active'")["n"]

    out["projects"] = fetch_one("SELECT COUNT(*) AS n FROM Project")["n"]
    out["active_projects"] = fetch_one(
        "SELECT COUNT(*) AS n FROM Project "
        "WHERE status IN ('planning','in_progress')")["n"]

    out["tasks"] = fetch_one("SELECT COUNT(*) AS n FROM Task")["n"]
    out["open_tasks"] = fetch_one(
        "SELECT COUNT(*) AS n FROM Task "
        "WHERE status NOT IN ('done','blocked')")["n"]

    out["invoices"] = fetch_one("SELECT COUNT(*) AS n FROM Invoice")["n"]
    out["outstanding_amount"] = fetch_one(
        "SELECT COALESCE(SUM(total_amount), 0) AS amt FROM Invoice "
        "WHERE status IN ('sent','overdue')")["amt"]

    bud = fetch_one(
        "SELECT COALESCE(SUM(budget),0) AS b, "
        "       COALESCE(SUM(actual_cost),0) AS a FROM Project")
    out["total_budget"] = bud["b"]
    out["actual_cost"] = bud["a"]
    out["budget_used_pct"] = (
        round(100.0 * float(bud["a"]) / float(bud["b"]), 1) if bud["b"] else 0.0
    )
    return out


def projects_by_status() -> list[dict]:
    order = ["planning", "in_progress", "on_hold", "completed", "cancelled"]
    rows = fetch_all(
        "SELECT status, COUNT(*) AS n FROM Project GROUP BY status")
    counts = {r["status"]: r["n"] for r in rows}
    return [{"status": s, "count": counts.get(s, 0)} for s in order]


def invoices_by_status() -> list[dict]:
    order = ["draft", "sent", "paid", "overdue", "cancelled"]
    rows = fetch_all(
        "SELECT status, COUNT(*) AS n, COALESCE(SUM(total_amount),0) AS amt "
        "FROM Invoice GROUP BY status")
    by = {r["status"]: r for r in rows}
    return [{"status": s,
             "count": by.get(s, {"n": 0})["n"],
             "amount": by.get(s, {"amt": 0})["amt"]} for s in order]


def top_projects_by_budget_usage(limit: int = 5) -> list[dict]:
    return fetch_all("""
        SELECT
            p.project_id, p.project_code, p.project_name, p.status,
            p.budget, p.actual_cost,
            CASE WHEN p.budget IS NULL OR p.budget = 0 THEN 0
                 ELSE ROUND(100.0 * COALESCE(p.actual_cost,0) / p.budget, 1)
            END AS pct_spent,
            c.customer_name
        FROM Project p
        LEFT JOIN Customer c ON c.customer_id = p.customer_id
        ORDER BY pct_spent DESC, p.budget DESC
        LIMIT :lim
    """, {"lim": limit})


def recent_risks(limit: int = 5) -> list[dict]:
    return fetch_all("""
        SELECT r.risk_id, r.description, r.probability, r.impact, r.status,
               r.identified_date, p.project_code, p.project_name
        FROM Project_Risk r
        JOIN Project p ON p.project_id = r.project_id
        ORDER BY r.identified_date DESC
        LIMIT :lim
    """, {"lim": limit})
