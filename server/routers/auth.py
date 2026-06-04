"""Login / logout / change-password routes."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from server import security
from server.db import execute, fetch_one


router = APIRouter()


def _templates(request: Request):
    return request.app.state.templates


GUEST_ROLES = [
    {"value": "admin",           "label": "Admin",           "description": "Full access to all features and settings"},
    {"value": "project_manager", "label": "Project Manager", "description": "Manage projects, resources, and reports"},
    {"value": "member",          "label": "Team Member",     "description": "View and update assigned work"},
    {"value": "viewer",          "label": "Viewer",          "description": "Read-only access to dashboards and reports"},
]

_VALID_ROLES = {r["value"] for r in GUEST_ROLES}


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if security.current_user(request) is not None:
        return RedirectResponse(url="/dashboard", status_code=303)
    return _templates(request).TemplateResponse(
        "login.html", {"request": request, "error": None, "roles": GUEST_ROLES})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    role: str = Form(...),
):
    if role not in _VALID_ROLES:
        return _templates(request).TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid role selected.", "roles": GUEST_ROLES},
            status_code=400,
        )
    request.session["user"] = {
        "user_id": 0,
        "username": f"guest_{role}",
        "role": role,
        "employee_id": None,
        "must_change_password": 0,
    }
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@router.get("/change-password", response_class=HTMLResponse)
def change_password_form(request: Request):
    user = security.require_user(request)
    return _templates(request).TemplateResponse(
        "change_password.html",
        {"request": request, "user": user, "error": None})


@router.post("/change-password", response_class=HTMLResponse)
def change_password_submit(
    request: Request,
    current: str = Form(...),
    new: str = Form(...),
    confirm: str = Form(...),
):
    user = security.require_user(request)
    error = None
    if new != confirm:
        error = "mismatch"
    elif len(new) < 6:
        error = "too_short"
    else:
        # Re-authenticate against current password
        from server.security import _is_postgres
        row = fetch_one(
            'SELECT password_hash, password_salt FROM "User" WHERE user_id = :id'
            if _is_postgres() else
            "SELECT password_hash, password_salt FROM User WHERE user_id = :id",
            {"id": user["user_id"]})
        if not row or not security.verify_password(
                current, row["password_hash"], row["password_salt"]):
            error = "wrong_current"
    if error:
        return _templates(request).TemplateResponse(
            "change_password.html",
            {"request": request, "user": user, "error": error},
            status_code=400,
        )

    h, s = security.hash_password(new)
    from server.security import _is_postgres
    execute(
        ('UPDATE "User" SET password_hash = :h, password_salt = :s, '
         "must_change_password = 0 WHERE user_id = :id"
         if _is_postgres() else
         "UPDATE User SET password_hash = :h, password_salt = :s, "
         "must_change_password = 0 WHERE user_id = :id"),
        {"h": h, "s": s, "id": user["user_id"]})

    user["must_change_password"] = 0
    request.session["user"] = user
    return RedirectResponse(url="/dashboard", status_code=303)
