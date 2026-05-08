"""Login / logout / change-password routes."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from server import security
from server.db import execute, fetch_one


router = APIRouter()


def _templates(request: Request):
    return request.app.state.templates


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if security.current_user(request) is not None:
        return RedirectResponse(url="/dashboard", status_code=303)
    return _templates(request).TemplateResponse(
        "login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    try:
        user = security.authenticate(username, password)
    except security.LoginError as exc:
        return _templates(request).TemplateResponse(
            "login.html",
            {"request": request, "error": exc.code, "username": username},
            status_code=401,
        )
    request.session["user"] = {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
        "employee_id": user.get("employee_id"),
        "must_change_password": user.get("must_change_password", 0),
    }
    if user.get("must_change_password"):
        return RedirectResponse(url="/change-password", status_code=303)
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
