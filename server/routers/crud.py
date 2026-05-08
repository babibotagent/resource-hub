"""Generic CRUD router — one set of routes handles all 11 data tables.

Routes:
    GET  /{view_id}              List
    GET  /{view_id}/new          Create form
    POST /{view_id}/new          Create submit
    GET  /{view_id}/{pk}/edit    Edit form
    POST /{view_id}/{pk}/edit    Edit submit
    POST /{view_id}/{pk}/delete  Delete
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from server import security
from server.db import fetch_all, fetch_one, execute
from server.crud_configs import VIEW_CONFIGS

router = APIRouter()


def _tpl(request: Request):
    return request.app.state.templates


def _cfg(view_id: str) -> dict:
    cfg = VIEW_CONFIGS.get(view_id)
    if cfg is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Unknown view: {view_id}")
    return cfg


def _quote_table(table: str) -> str:
    """Quote table name for Postgres compatibility (reserved words)."""
    from server.security import _is_postgres
    if _is_postgres():
        return f'"{table}"'
    return table


def _form_value(field: dict, raw: str | None) -> Any:
    """Convert form POST value to the right Python type for SQL."""
    if raw is None or raw.strip() == '':
        return None
    raw = raw.strip()
    ftype = field.get('type', 'text')
    if ftype in ('int',):
        return int(raw)
    if ftype in ('real',):
        return float(raw)
    return raw


def _resolve_choices(field: dict) -> list[tuple]:
    """Call the choices_fn to get FK options."""
    fn = field.get('choices_fn')
    if fn:
        try:
            return fn()
        except Exception:
            return []
    return []


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------
@router.get("/{view_id}", response_class=HTMLResponse)
def crud_list(request: Request, view_id: str):
    user = security.require_user(request)
    cfg = _cfg(view_id)
    sql = cfg['list_sql'] + " " + cfg.get('list_order', '')
    rows = fetch_all(sql)
    return _tpl(request).TemplateResponse("crud_list.html", {
        "request": request,
        "user": user,
        "active": view_id,
        "cfg": cfg,
        "view_id": view_id,
        "rows": rows,
        "columns": cfg['columns'],
    })


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------
@router.get("/{view_id}/new", response_class=HTMLResponse)
def crud_new_form(request: Request, view_id: str):
    user = security.require_user(request)
    cfg = _cfg(view_id)
    fields = _prepare_fields(cfg, row=None)
    return _tpl(request).TemplateResponse("crud_form.html", {
        "request": request,
        "user": user,
        "active": view_id,
        "cfg": cfg,
        "view_id": view_id,
        "fields": fields,
        "row": None,
        "pk_val": None,
        "error": None,
    })


@router.post("/{view_id}/new", response_class=HTMLResponse)
async def crud_new_submit(request: Request, view_id: str):
    user = security.require_user(request)
    cfg = _cfg(view_id)
    form = await request.form()

    cols, vals, params = [], [], {}
    for f in cfg['form_fields']:
        k = f['key']
        v = _form_value(f, form.get(k))
        cols.append(k)
        vals.append(f":{k}")
        params[k] = v

    # Auto-now fields (e.g. created_at)
    for af in cfg.get('auto_now', []):
        cols.append(af)
        vals.append(f":{af}")
        params[af] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    table = _quote_table(cfg['table'])
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(vals)})"

    try:
        execute(sql, params)
    except Exception as exc:
        fields = _prepare_fields(cfg, row=None, form_data=form)
        return _tpl(request).TemplateResponse("crud_form.html", {
            "request": request,
            "user": user,
            "active": view_id,
            "cfg": cfg,
            "view_id": view_id,
            "fields": fields,
            "row": None,
            "pk_val": None,
            "error": str(exc),
        }, status_code=400)

    return RedirectResponse(url=f"/{view_id}", status_code=303)


# ---------------------------------------------------------------------------
# EDIT
# ---------------------------------------------------------------------------
@router.get("/{view_id}/{pk_val}/edit", response_class=HTMLResponse)
def crud_edit_form(request: Request, view_id: str, pk_val: int):
    user = security.require_user(request)
    cfg = _cfg(view_id)
    table = _quote_table(cfg['table'])
    row = fetch_one(f"SELECT * FROM {table} WHERE {cfg['pk']} = :pk", {"pk": pk_val})
    if row is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Record not found")

    fields = _prepare_fields(cfg, row=row)
    return _tpl(request).TemplateResponse("crud_form.html", {
        "request": request,
        "user": user,
        "active": view_id,
        "cfg": cfg,
        "view_id": view_id,
        "fields": fields,
        "row": row,
        "pk_val": pk_val,
        "error": None,
    })


@router.post("/{view_id}/{pk_val}/edit", response_class=HTMLResponse)
async def crud_edit_submit(request: Request, view_id: str, pk_val: int):
    user = security.require_user(request)
    cfg = _cfg(view_id)
    form = await request.form()

    sets, params = [], {"pk": pk_val}
    for f in cfg['form_fields']:
        k = f['key']
        v = _form_value(f, form.get(k))
        sets.append(f"{k} = :{k}")
        params[k] = v

    table = _quote_table(cfg['table'])
    sql = f"UPDATE {table} SET {', '.join(sets)} WHERE {cfg['pk']} = :pk"

    try:
        execute(sql, params)
    except Exception as exc:
        fields = _prepare_fields(cfg, row=None, form_data=form)
        return _tpl(request).TemplateResponse("crud_form.html", {
            "request": request,
            "user": user,
            "active": view_id,
            "cfg": cfg,
            "view_id": view_id,
            "fields": fields,
            "row": dict(form),
            "pk_val": pk_val,
            "error": str(exc),
        }, status_code=400)

    return RedirectResponse(url=f"/{view_id}", status_code=303)


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------
@router.post("/{view_id}/{pk_val}/delete")
def crud_delete(request: Request, view_id: str, pk_val: int):
    security.require_user(request)
    cfg = _cfg(view_id)
    table = _quote_table(cfg['table'])
    execute(f"DELETE FROM {table} WHERE {cfg['pk']} = :pk", {"pk": pk_val})
    return RedirectResponse(url=f"/{view_id}", status_code=303)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _prepare_fields(cfg: dict, row: dict | None = None,
                    form_data=None) -> list[dict]:
    """Augment each form_field with its current value and FK choices."""
    out = []
    for f in cfg['form_fields']:
        entry = dict(f)  # shallow copy
        k = f['key']
        # Current value: prefer form submission, fall back to DB row
        if form_data is not None:
            entry['value'] = form_data.get(k, '')
        elif row is not None:
            entry['value'] = row.get(k, '')
        else:
            entry['value'] = f.get('default', '')

        # FK choices
        if f.get('type') == 'fk':
            entry['choices'] = _resolve_choices(f)

        out.append(entry)
    return out
