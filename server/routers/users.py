"""User management routes (admin only)."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from server import security
from server.db import fetch_all, fetch_one, execute
from server.crud_configs import USER_ROLES

router = APIRouter(prefix="/users")


def _tpl(request: Request):
    return request.app.state.templates


def _qt():
    from server.security import _is_postgres
    return '"User"' if _is_postgres() else 'User'


@router.get("", response_class=HTMLResponse)
def user_list(request: Request):
    user = security.require_admin(request)
    rows = fetch_all(f"SELECT user_id, username, role, is_active, last_login_at, created_at FROM {_qt()} ORDER BY username")
    return _tpl(request).TemplateResponse(request, name="users_list.html", context={
        "request": request, "user": user, "active": "users", "rows": rows,
    })


@router.get("/new", response_class=HTMLResponse)
def user_new_form(request: Request):
    user = security.require_admin(request)
    return _tpl(request).TemplateResponse(request, name="users_form.html", context={
        "request": request, "user": user, "active": "users",
        "roles": USER_ROLES, "row": None, "error": None,
    })


@router.post("/new", response_class=HTMLResponse)
def user_new_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("viewer"),
):
    user = security.require_admin(request)
    if len(password) < 6:
        return _tpl(request).TemplateResponse(request, name="users_form.html", context={
            "request": request, "user": user, "active": "users",
            "roles": USER_ROLES, "row": {"username": username, "role": role},
            "error": "Password must be at least 6 characters.",
        }, status_code=400)

    h, s = security.hash_password(password)
    try:
        execute(
            f"INSERT INTO {_qt()} (username, password_hash, password_salt, role, "
            "is_active, must_change_password, created_at) "
            "VALUES (:u, :h, :s, :r, 1, 1, :now)",
            {"u": username.strip(), "h": h, "s": s, "r": role,
             "now": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")})
    except Exception as exc:
        return _tpl(request).TemplateResponse(request, name="users_form.html", context={
            "request": request, "user": user, "active": "users",
            "roles": USER_ROLES, "row": {"username": username, "role": role},
            "error": str(exc),
        }, status_code=400)
    return RedirectResponse(url="/users", status_code=303)


@router.get("/{uid}/edit", response_class=HTMLResponse)
def user_edit_form(request: Request, uid: int):
    user = security.require_admin(request)
    row = fetch_one(f"SELECT * FROM {_qt()} WHERE user_id = :id", {"id": uid})
    if row is None:
        from fastapi import HTTPException
        raise HTTPException(404, "User not found")
    return _tpl(request).TemplateResponse(request, name="users_form.html", context={
        "request": request, "user": user, "active": "users",
        "roles": USER_ROLES, "row": row, "error": None,
    })


@router.post("/{uid}/edit", response_class=HTMLResponse)
def user_edit_submit(
    request: Request, uid: int,
    username: str = Form(...),
    role: str = Form("viewer"),
    is_active: int = Form(1),
    password: str = Form(""),
):
    user = security.require_admin(request)
    if password and len(password) < 6:
        row = fetch_one(f"SELECT * FROM {_qt()} WHERE user_id = :id", {"id": uid})
        return _tpl(request).TemplateResponse(request, name="users_form.html", context={
            "request": request, "user": user, "active": "users",
            "roles": USER_ROLES, "row": row,
            "error": "Password must be at least 6 characters.",
        }, status_code=400)

    if password:
        h, s = security.hash_password(password)
        execute(
            f"UPDATE {_qt()} SET username=:u, role=:r, is_active=:a, "
            "password_hash=:h, password_salt=:s, must_change_password=1 WHERE user_id=:id",
            {"u": username.strip(), "r": role, "a": is_active, "h": h, "s": s, "id": uid})
    else:
        execute(
            f"UPDATE {_qt()} SET username=:u, role=:r, is_active=:a WHERE user_id=:id",
            {"u": username.strip(), "r": role, "a": is_active, "id": uid})
    return RedirectResponse(url="/users", status_code=303)
