"""
Read-only query helpers for the new 12-table schema.

All queries that touch project-scoped data honour the current user's
visibility (auth.visible_project_ids()):
  * Admins see everything (no filter applied).
  * Other roles see only the projects in User_Project_Access for them.

Each function returns plain Python data structures (dicts / lists), so the
Tkinter views can stay thin and the same queries can power CLI tools, tests
or a future web/REST API without changes.
"""

from __future__ import annotations

from typing import Any, Optional

import auth
from database import get_connection


def _rows(cur):
    return [dict(r) for r in cur.fetchall()]


def _project_filter():
    """Return (sql_clause, params) to AND-into a query that has a project_id column.

    For admin (or no user) returns ('', ()). For other roles returns
    something like (' AND p.project_id IN (?, ?)', (1, 2)). When the user
    has no projects we use a clause that matches no rows.
    """
    ids = auth.visible_project_ids()
    if ids is None:
        return '', ()
    if not ids:
        return ' AND 1 = 0', ()
    placeholders = ','.join('?' for _ in ids)
    return f' AND project_id IN ({placeholders})', tuple(ids)


def _alias_filter(alias: str = 'p'):
    """Same as ``_project_filter`` but with a custom table alias prefix."""
    ids = auth.visible_project_ids()
    if ids is None:
        return '', ()
    if not ids:
        return ' AND 1 = 0', ()
    placeholders = ','.join('?' for _ in ids)
    return f' AND {alias}.project_id IN ({placeholders})', tuple(ids)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
def dashboard_kpis():
    """Top-line numbers shown on the dashboard."""
    proj_clause, proj_params = _project_filter()

    with get_connection() as conn:
        cur = conn.cursor()
        out = {}

        # People-related counts are always full (admins create users; non-admins
        # don't really 'see' employees beyond their projects, but employees
        # aren't sensitive enough to hide).
        cur.execute("SELECT COUNT(*) AS n FROM Employee WHERE status = 'active'")
        out['employees'] = cur.fetchone()['n']

        cur.execute("SELECT COUNT(*) AS n FROM External_Resource WHERE status = 'active'")
        out['externals'] = cur.fetchone()['n']

        cur.execute("SELECT COUNT(*) AS n FROM Customer WHERE status = 'active'")
        out['customers'] = cur.fetchone()['n']

        # Project counts apply project visibility filter.
        cur.execute(f"SELECT COUNT(*) AS n FROM Project WHERE 1=1{proj_clause}",
                    proj_params)
        out['projects'] = cur.fetchone()['n']
        cur.execute(
            f"SELECT COUNT(*) AS n FROM Project "
            f"WHERE status IN ('planning','in_progress'){proj_clause}", proj_params)
        out['active_projects'] = cur.fetchone()['n']

        cur.execute(f"SELECT COUNT(*) AS n FROM Task WHERE 1=1{proj_clause}",
                    proj_params)
        out['tasks'] = cur.fetchone()['n']
        cur.execute(
            f"SELECT COUNT(*) AS n FROM Task "
            f"WHERE status NOT IN ('done','blocked'){proj_clause}", proj_params)
        out['open_tasks'] = cur.fetchone()['n']

        cur.execute(f"SELECT COUNT(*) AS n FROM Invoice WHERE 1=1{proj_clause}",
                    proj_params)
        out['invoices'] = cur.fetchone()['n']
        cur.execute(
            f"SELECT COALESCE(SUM(total_amount),0) AS amt FROM Invoice "
            f"WHERE status IN ('sent','overdue'){proj_clause}", proj_params)
        out['outstanding_amount'] = cur.fetchone()['amt']

        cur.execute(
            f"SELECT COALESCE(SUM(budget),0) AS b, "
            f"       COALESCE(SUM(actual_cost),0) AS a FROM Project "
            f"WHERE 1=1{proj_clause}", proj_params)
        row = cur.fetchone()
        out['total_budget'] = row['b']
        out['actual_cost']  = row['a']
        out['budget_used_pct'] = (
            round(100.0 * row['a'] / row['b'], 1) if row['b'] else 0.0
        )

        return out


def projects_by_status():
    proj_clause, proj_params = _project_filter()
    order = ['planning', 'in_progress', 'on_hold', 'completed', 'cancelled']
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT status, COUNT(*) AS n FROM Project "
            f"WHERE 1=1{proj_clause} GROUP BY status", proj_params)
        counts = {r['status']: r['n'] for r in cur.fetchall()}
    return [{'status': s, 'count': counts.get(s, 0)} for s in order]


def invoices_by_status():
    proj_clause, proj_params = _project_filter()
    order = ['draft', 'sent', 'paid', 'overdue', 'cancelled']
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT status, COUNT(*) AS n, COALESCE(SUM(total_amount),0) AS amt "
            f"FROM Invoice WHERE 1=1{proj_clause} GROUP BY status", proj_params)
        rows = {r['status']: (r['n'], r['amt']) for r in cur.fetchall()}
    return [{'status': s,
             'count': rows.get(s, (0, 0))[0],
             'amount': rows.get(s, (0, 0))[1]} for s in order]


def top_projects_by_budget_usage(limit=5):
    proj_clause, proj_params = _alias_filter('p')
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT
                p.project_id, p.project_code, p.project_name, p.status,
                p.budget, p.actual_cost,
                CASE WHEN p.budget IS NULL OR p.budget = 0 THEN 0
                     ELSE ROUND(100.0 * COALESCE(p.actual_cost,0) / p.budget, 1)
                END AS pct_spent,
                c.customer_name
            FROM Project p
            LEFT JOIN Customer c ON c.customer_id = p.customer_id
            WHERE 1=1{proj_clause}
            ORDER BY pct_spent DESC, p.budget DESC
            LIMIT ?
        """, proj_params + (limit,))
        return _rows(cur)


def recent_risks(limit=5):
    proj_clause, proj_params = _alias_filter('r')
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT
                r.risk_id, r.description, r.probability, r.impact, r.status,
                r.identified_date, p.project_code, p.project_name
            FROM Project_Risk r
            JOIN Project p ON p.project_id = r.project_id
            WHERE 1=1{proj_clause}
            ORDER BY r.identified_date DESC
            LIMIT ?
        """, proj_params + (limit,))
        return _rows(cur)


# ---------------------------------------------------------------------------
# Project list (used later by the projects view)
# ---------------------------------------------------------------------------
def list_projects():
    proj_clause, proj_params = _alias_filter('p')
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT p.*, c.customer_name
            FROM Project p
            LEFT JOIN Customer c ON c.customer_id = p.customer_id
            WHERE 1=1{proj_clause}
            ORDER BY p.start_date DESC, p.project_code
        """, proj_params)
        return _rows(cur)


def project_team(project_id):
    """All resources assigned to a project, internal + external.

    The caller is expected to check ``auth.can_access_project`` first.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                a.assignment_id, a.role_in_project, a.allocated_hours,
                a.start_date, a.end_date,
                COALESCE(e.first_name || ' ' || e.last_name,
                         x.first_name || ' ' || x.last_name) AS person_name,
                CASE WHEN e.employee_id IS NOT NULL THEN 'internal'
                     ELSE 'external' END AS kind,
                COALESCE(e.email, x.email) AS email
            FROM Project_Assignment a
            LEFT JOIN Employee          e ON e.employee_id = a.employee_id
            LEFT JOIN External_Resource x ON x.external_id = a.external_id
            WHERE a.project_id = ?
            ORDER BY a.start_date
        """, (project_id,))
        return _rows(cur)


if __name__ == '__main__':
    import json
    print(json.dumps({
        'kpis':                 dashboard_kpis(),
        'projects_by_status':   projects_by_status(),
        'invoices_by_status':   invoices_by_status(),
        'top_projects':         top_projects_by_budget_usage(),
        'recent_risks':         recent_risks(),
    }, indent=2, default=str))
