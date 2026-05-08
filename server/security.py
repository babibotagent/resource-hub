"""Web auth: PBKDF2 password hashing (matches legacy auth.py) + cookie sessions.

We deliberately keep the same hashing parameters as the desktop app so existing
User rows continue to work without re-hashing.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import Any, Optional

from fastapi import Request

from server.db import fetch_one, execute


_HASH_ALGO = "sha256"
_HASH_ITERATIONS = 200_000
_SALT_BYTES = 16


def _hash(password: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac(_HASH_ALGO, password.encode("utf-8"),
                                 salt, _HASH_ITERATIONS)
    return digest.hex()


def hash_password(password: str) -> tuple[str, str]:
    if not password:
        raise ValueError("password must not be empty")
    salt_hex = secrets.token_hex(_SALT_BYTES)
    return _hash(password, salt_hex), salt_hex


def verify_password(password: str, hash_hex: str, salt_hex: str) -> bool:
    return secrets.compare_digest(_hash(password, salt_hex), hash_hex)


# ---------------------------------------------------------------------------
# Login / session
# ---------------------------------------------------------------------------
class LoginError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def authenticate(username: str, password: str) -> dict[str, Any]:
    """Return the user row (without password fields) on success, raise otherwise."""
    username = (username or "").strip()
    if not username or not password:
        raise LoginError("empty_credentials")

    row = fetch_one(
        'SELECT * FROM "User" WHERE username = :u' if _is_postgres()
        else "SELECT * FROM User WHERE username = :u",
        {"u": username})
    if row is None:
        raise LoginError("unknown_user")
    if not row["is_active"]:
        raise LoginError("inactive_user")
    if not verify_password(password, row["password_hash"], row["password_salt"]):
        raise LoginError("bad_password")

    # Update last_login_at
    execute(
        ('UPDATE "User" SET last_login_at = :now WHERE user_id = :id'
         if _is_postgres() else
         "UPDATE User SET last_login_at = :now WHERE user_id = :id"),
        {"now": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
         "id": row["user_id"]})

    row.pop("password_hash", None)
    row.pop("password_salt", None)
    return row


def _is_postgres() -> bool:
    from server.settings import DATABASE_URL
    return DATABASE_URL.startswith("postgres")


def ensure_default_admin() -> bool:
    """Create admin/admin if no users exist."""
    if _is_postgres():
        cnt = fetch_one('SELECT COUNT(*) AS n FROM "User"')
    else:
        cnt = fetch_one("SELECT COUNT(*) AS n FROM User")
    if cnt and cnt["n"] > 0:
        return False
    h, s = hash_password("admin")
    execute(
        ('INSERT INTO "User" (username, password_hash, password_salt, role, '
         'employee_id, is_active, must_change_password, created_at) '
         "VALUES (:u, :h, :s, 'admin', NULL, 1, 1, :now)"
         if _is_postgres() else
         "INSERT INTO User (username, password_hash, password_salt, role, "
         "employee_id, is_active, must_change_password, created_at) "
         "VALUES (:u, :h, :s, 'admin', NULL, 1, 1, :now)"),
        {"u": "admin", "h": h, "s": s,
         "now": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")})
    return True


# ---------------------------------------------------------------------------
# Request helpers
# ---------------------------------------------------------------------------
def current_user(request: Request) -> Optional[dict]:
    """Return the logged-in user dict (or None)."""
    return request.session.get("user")


def require_user(request: Request) -> dict:
    user = current_user(request)
    if user is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def require_admin(request: Request) -> dict:
    u = require_user(request)
    if u.get("role") != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin only")
    return u
