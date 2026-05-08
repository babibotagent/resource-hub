"""
Authentication and authorisation for ResourceHub.

Roles
-----
- admin            : full access to everything (sees all 12 tables, can manage users)
- project_manager  : full edit of projects they have access to (Project, Task,
                     Project_Assignment, Project_Risk, Time_Entry, Invoice on
                     their projects). Read-only for the rest.
- member           : edit Task/Time_Entry on their projects, read other entities.
- viewer           : read-only on assigned projects.

Per-project access lives in ``User_Project_Access``.

Password storage
----------------
PBKDF2-HMAC-SHA256, 200 000 iterations, random 16-byte salt, hex-encoded.
No external dependency (stdlib only).

Session
-------
Single-user desktop app, so the "session" is just a module-level variable
holding the currently logged-in user. ``login()`` populates it,
``logout()`` clears it.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime
from typing import Any, Iterable, Optional

from database import get_connection


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
_HASH_ALGO = 'sha256'
_HASH_ITERATIONS = 200_000
_SALT_BYTES = 16


def _hash(password: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac(_HASH_ALGO, password.encode('utf-8'),
                                 salt, _HASH_ITERATIONS)
    return digest.hex()


def hash_password(password: str) -> tuple[str, str]:
    """Return (hash_hex, salt_hex) for a fresh password."""
    if not password:
        raise ValueError("password must not be empty")
    salt_hex = secrets.token_hex(_SALT_BYTES)
    return _hash(password, salt_hex), salt_hex


def verify_password(password: str, hash_hex: str, salt_hex: str) -> bool:
    return secrets.compare_digest(_hash(password, salt_hex), hash_hex)


# ---------------------------------------------------------------------------
# Module session state
# ---------------------------------------------------------------------------
_current_user: Optional[dict[str, Any]] = None
_listeners: list = []  # callbacks(new_user_or_none)


def add_listener(cb) -> None:
    if cb not in _listeners:
        _listeners.append(cb)


def remove_listener(cb) -> None:
    if cb in _listeners:
        _listeners.remove(cb)


def _notify() -> None:
    for cb in list(_listeners):
        try:
            cb(_current_user)
        except Exception:
            pass


def current_user() -> Optional[dict[str, Any]]:
    return _current_user


def is_authenticated() -> bool:
    return _current_user is not None


def is_admin() -> bool:
    return bool(_current_user) and _current_user.get('role') == 'admin'


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
def ensure_default_admin() -> bool:
    """Create the default admin (admin/admin) if no users exist yet.

    Returns True if a user was created, False otherwise. Sets
    ``must_change_password`` so the first login forces a change.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS n FROM User")
        if cur.fetchone()['n'] > 0:
            return False
        h, s = hash_password('admin')
        cur.execute("""
            INSERT INTO User (
                username, password_hash, password_salt, role,
                employee_id, is_active, must_change_password, created_at
            ) VALUES (?, ?, ?, 'admin', NULL, 1, 1, ?)
        """, ('admin', h, s, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))
    return True


# ---------------------------------------------------------------------------
# Login / logout
# ---------------------------------------------------------------------------
class LoginError(Exception):
    """Raised when login fails. ``code`` lets the UI pick the right i18n key."""
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def login(username: str, password: str) -> dict[str, Any]:
    """Validate credentials and set the session user.

    Raises ``LoginError`` with one of:
      * ``unknown_user``    - no such username
      * ``inactive_user``   - account marked inactive
      * ``bad_password``    - password mismatch
    """
    global _current_user
    username = (username or '').strip()
    if not username or not password:
        raise LoginError('empty_credentials')

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM User WHERE username = ?", (username,))
        row = cur.fetchone()
        if row is None:
            raise LoginError('unknown_user')
        user = dict(row)
        if not user['is_active']:
            raise LoginError('inactive_user')
        if not verify_password(password, user['password_hash'], user['password_salt']):
            raise LoginError('bad_password')

        # Update last_login_at (best effort; not critical to login flow)
        cur.execute("UPDATE User SET last_login_at = ? WHERE user_id = ?",
                    (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), user['user_id']))

    # Strip secret fields before stashing
    user.pop('password_hash', None)
    user.pop('password_salt', None)
    _current_user = user
    _notify()
    return user


def logout() -> None:
    global _current_user
    _current_user = None
    _notify()


def set_password(user_id: int, new_password: str, *,
                 clear_must_change: bool = True) -> None:
    """Update a user's password. Clears the must-change flag by default."""
    if not new_password or len(new_password) < 4:
        raise ValueError("password too short (minimum 4 characters)")
    h, s = hash_password(new_password)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE User
               SET password_hash = ?, password_salt = ?,
                   must_change_password = ?
             WHERE user_id = ?
        """, (h, s, 0 if clear_must_change else 1, user_id))
    # Refresh in-memory current_user if it's the same user
    global _current_user
    if _current_user and _current_user.get('user_id') == user_id:
        if clear_must_change:
            _current_user['must_change_password'] = 0


# ---------------------------------------------------------------------------
# Authorisation
# ---------------------------------------------------------------------------
# Action keys are short strings like 'project.edit', 'invoice.create',
# 'user.manage'. The matrix below describes who can do what at the global
# level (i.e. what the role unlocks regardless of project). Per-project
# scoping is then layered on top by ``can_access_project``.
GLOBAL_PERMISSIONS: dict[str, set[str]] = {
    'admin': {
        'user.manage',
        'department.manage',
        'employee.manage',
        'external.manage',
        'customer.manage',
        'knowledge.manage',
        'project.create',
        'project.delete',
        'invoice.manage_all',
        'reports.view',
    },
    'project_manager': {
        'project.create',
        'reports.view',
    },
    'member':  set(),
    'viewer':  set(),
}


def has_permission(action: str) -> bool:
    """True if the current user's role grants this *global* action."""
    if not _current_user:
        return False
    return action in GLOBAL_PERMISSIONS.get(_current_user['role'], set())


def can_access_project(project_id: int, *, write: bool = False) -> bool:
    """Whether the current user may see/edit a specific project."""
    if not _current_user:
        return False
    if _current_user['role'] == 'admin':
        return True
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT project_role FROM User_Project_Access
                        WHERE user_id = ? AND project_id = ?""",
                    (_current_user['user_id'], project_id))
        row = cur.fetchone()
    if row is None:
        return False
    if not write:
        return True  # any access role grants read
    # Write requires PM (any role) or member if user's role allows write
    project_role = row['project_role']
    if project_role == 'project_manager':
        return True
    if project_role == 'member' and _current_user['role'] in ('project_manager', 'member'):
        return True
    return False  # viewer = read only


def visible_project_ids() -> Optional[list[int]]:
    """List of projects the current user can see.

    Returns ``None`` for admin (meaning "no filter, see everything"). For
    everyone else returns the list of project IDs they have access to (may
    be empty).
    """
    if not _current_user:
        return []  # not logged in: nothing
    if _current_user['role'] == 'admin':
        return None
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT project_id FROM User_Project_Access
                        WHERE user_id = ?""", (_current_user['user_id'],))
        return [r['project_id'] for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# User management (admin operations)
# ---------------------------------------------------------------------------
def list_users() -> list[dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.user_id, u.username, u.role, u.is_active,
                   u.must_change_password, u.created_at, u.last_login_at,
                   u.employee_id,
                   COALESCE(e.first_name || ' ' || e.last_name, '') AS employee_name
              FROM User u
              LEFT JOIN Employee e ON e.employee_id = u.employee_id
             ORDER BY u.username
        """)
        return [dict(r) for r in cur.fetchall()]


def create_user(username: str, password: str, role: str,
                employee_id: Optional[int] = None,
                must_change: bool = False) -> int:
    if role not in ('admin', 'project_manager', 'member', 'viewer'):
        raise ValueError(f"invalid role: {role!r}")
    h, s = hash_password(password)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO User (
                username, password_hash, password_salt, role,
                employee_id, is_active, must_change_password, created_at
            ) VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """, (username, h, s, role, employee_id,
              1 if must_change else 0,
              datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))
        return cur.lastrowid


def update_user(user_id: int, *, username: Optional[str] = None,
                role: Optional[str] = None,
                employee_id: Optional[int] = None,
                is_active: Optional[bool] = None) -> None:
    sets, params = [], []
    if username is not None:
        sets.append("username = ?"); params.append(username)
    if role is not None:
        if role not in ('admin', 'project_manager', 'member', 'viewer'):
            raise ValueError(f"invalid role: {role!r}")
        sets.append("role = ?"); params.append(role)
    if employee_id is not None:
        sets.append("employee_id = ?")
        params.append(employee_id if employee_id else None)
    if is_active is not None:
        sets.append("is_active = ?"); params.append(1 if is_active else 0)
    if not sets:
        return
    params.append(user_id)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE User SET {', '.join(sets)} WHERE user_id = ?", params)


def delete_user(user_id: int) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM User WHERE user_id = ?", (user_id,))


def grant_project_access(user_id: int, project_id: int, project_role: str) -> None:
    if project_role not in ('project_manager', 'member', 'viewer'):
        raise ValueError(f"invalid project_role: {project_role!r}")
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO User_Project_Access (user_id, project_id, project_role, granted_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, project_id) DO UPDATE SET project_role = excluded.project_role
        """, (user_id, project_id, project_role,
              datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))


def revoke_project_access(user_id: int, project_id: int) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""DELETE FROM User_Project_Access
                        WHERE user_id = ? AND project_id = ?""",
                    (user_id, project_id))


def list_project_access(user_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT upa.access_id, upa.project_id, upa.project_role,
                   upa.granted_at, p.project_code, p.project_name
              FROM User_Project_Access upa
              JOIN Project p ON p.project_id = upa.project_id
             WHERE upa.user_id = ?
             ORDER BY p.project_code
        """, (user_id,))
        return [dict(r) for r in cur.fetchall()]
