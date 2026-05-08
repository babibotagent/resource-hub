"""
ResourceHub v2 - Database layer
Project Management schema with 12 data tables + auth tables (User,
User_Project_Access), derived from DB_Tables_ProjectManagement.xlsx.

Design notes
------------
- SQLite, single file at data/projects.db (override with RESOURCEHUB_DB_PATH).
- ENUMs implemented as TEXT with CHECK constraints.
- All FKs enforced (PRAGMA foreign_keys = ON).
- UNIQUE on the business codes: employee_code, customer_code, project_code,
  invoice_number, cost_center, and on emails where the dictionary requires it.
- Department.manager_employee_id and Employee.department_id form a cycle.
  We make Department.manager_employee_id nullable so we can insert
  Departments first, then Employees, then UPDATE departments with managers
  (see import_excel.py).
- Project_Assignment, Task and Time_Entry have a "one of two FKs" pattern
  (employee_id XOR external_id). We enforce it with a CHECK constraint
  (Task allows both NULL = unassigned).
- User and User_Project_Access power authentication and per-project access.
"""

import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get(
    'RESOURCEHUB_DB_PATH',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'projects.db'),
)


@contextmanager
def get_connection():
    """Context manager: opens the DB, enables FKs, commits/rollbacks."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS Department (
        department_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        department_name      TEXT    NOT NULL,
        manager_employee_id  INTEGER,
        cost_center          TEXT    UNIQUE,
        status               TEXT    CHECK (status IN ('active','inactive')),
        created_at           TEXT    NOT NULL,
        FOREIGN KEY (manager_employee_id) REFERENCES Employee(employee_id)
            ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Employee (
        employee_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name     TEXT    NOT NULL,
        last_name      TEXT    NOT NULL,
        employee_code  TEXT    UNIQUE,
        email          TEXT    UNIQUE,
        phone          TEXT,
        role           TEXT    NOT NULL,
        department_id  INTEGER,
        hourly_rate    REAL    NOT NULL,
        hire_date      TEXT    NOT NULL,
        status         TEXT    CHECK (status IN ('active','inactive')),
        created_at     TEXT    NOT NULL,
        FOREIGN KEY (department_id) REFERENCES Department(department_id)
            ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS External_Resource (
        external_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name      TEXT NOT NULL,
        last_name       TEXT NOT NULL,
        company         TEXT,
        email           TEXT UNIQUE,
        phone           TEXT,
        hourly_rate     REAL NOT NULL,
        contract_type   TEXT CHECK (contract_type IN ('freelancer','outsource','consultant')),
        specialty       TEXT,
        status          TEXT CHECK (status IN ('active','inactive')),
        contract_start  TEXT NOT NULL,
        contract_end    TEXT,
        created_at      TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Customer (
        customer_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name  TEXT NOT NULL,
        customer_code  TEXT UNIQUE,
        contact_name   TEXT,
        contact_email  TEXT,
        contact_phone  TEXT,
        industry       TEXT,
        address        TEXT,
        country        TEXT,
        payment_terms  TEXT CHECK (payment_terms IN ('NET30','NET60','NET90')),
        status         TEXT CHECK (status IN ('active','inactive')),
        created_at     TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Knowledge (
        knowledge_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        subject       TEXT NOT NULL,
        category      TEXT CHECK (category IN
                            ('Frontend','Backend','Design','DevOps','PM','QA','Data','Mobile')),
        description   TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Project (
        project_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name     TEXT NOT NULL,
        project_code     TEXT UNIQUE,
        customer_id      INTEGER,
        description      TEXT,
        status           TEXT CHECK (status IN
                                ('planning','in_progress','on_hold','completed','cancelled')),
        priority         TEXT CHECK (priority IN ('low','medium','high','critical')),
        estimated_hours  REAL,
        actual_hours     REAL,
        budget           REAL,
        actual_cost      REAL,
        start_date       TEXT,
        end_date         TEXT,
        created_at       TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Task (
        task_id               INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id            INTEGER NOT NULL,
        title                 TEXT NOT NULL,
        description           TEXT,
        assigned_employee_id  INTEGER,
        assigned_external_id  INTEGER,
        status                TEXT CHECK (status IN
                                    ('todo','in_progress','in_review','done','blocked')),
        priority              TEXT CHECK (priority IN ('low','medium','high','critical')),
        estimated_hours       REAL,
        actual_hours          REAL,
        due_date              TEXT,
        completed_date        TEXT,
        created_at            TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES Project(project_id) ON DELETE CASCADE,
        FOREIGN KEY (assigned_employee_id) REFERENCES Employee(employee_id)
            ON DELETE SET NULL,
        FOREIGN KEY (assigned_external_id) REFERENCES External_Resource(external_id)
            ON DELETE SET NULL,
        CHECK (
            (assigned_employee_id IS NOT NULL AND assigned_external_id IS NULL)
         OR (assigned_employee_id IS NULL     AND assigned_external_id IS NOT NULL)
         OR (assigned_employee_id IS NULL     AND assigned_external_id IS NULL)
        )
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Project_Assignment (
        assignment_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id       INTEGER NOT NULL,
        employee_id      INTEGER,
        external_id      INTEGER,
        role_in_project  TEXT,
        allocated_hours  REAL,
        start_date       TEXT,
        end_date         TEXT,
        FOREIGN KEY (project_id)  REFERENCES Project(project_id) ON DELETE CASCADE,
        FOREIGN KEY (employee_id) REFERENCES Employee(employee_id) ON DELETE SET NULL,
        FOREIGN KEY (external_id) REFERENCES External_Resource(external_id) ON DELETE SET NULL,
        CHECK (
            (employee_id IS NOT NULL AND external_id IS NULL)
         OR (employee_id IS NULL     AND external_id IS NOT NULL)
        )
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Employee_Knowledge (
        employee_knowledge_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id            INTEGER NOT NULL,
        knowledge_id           INTEGER NOT NULL,
        years_experience       INTEGER,
        proficiency            TEXT CHECK (proficiency IN ('junior','mid','senior','expert')),
        FOREIGN KEY (employee_id)  REFERENCES Employee(employee_id)   ON DELETE CASCADE,
        FOREIGN KEY (knowledge_id) REFERENCES Knowledge(knowledge_id) ON DELETE CASCADE,
        UNIQUE (employee_id, knowledge_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Time_Entry (
        time_entry_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id        INTEGER NOT NULL,
        employee_id    INTEGER,
        external_id    INTEGER,
        date           TEXT NOT NULL,
        hours          REAL NOT NULL,
        description    TEXT,
        billable       TEXT CHECK (billable IN ('yes','no')),
        FOREIGN KEY (task_id)     REFERENCES Task(task_id)             ON DELETE CASCADE,
        FOREIGN KEY (employee_id) REFERENCES Employee(employee_id)     ON DELETE SET NULL,
        FOREIGN KEY (external_id) REFERENCES External_Resource(external_id) ON DELETE SET NULL,
        CHECK (
            (employee_id IS NOT NULL AND external_id IS NULL)
         OR (employee_id IS NULL     AND external_id IS NOT NULL)
        )
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Project_Risk (
        risk_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id       INTEGER NOT NULL,
        description      TEXT NOT NULL,
        probability      TEXT CHECK (probability IN ('low','medium','high')),
        impact           TEXT CHECK (impact IN ('low','medium','high')),
        mitigation_plan  TEXT,
        status           TEXT CHECK (status IN ('identified','mitigating','resolved','accepted')),
        identified_date  TEXT,
        FOREIGN KEY (project_id) REFERENCES Project(project_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Invoice (
        invoice_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id      INTEGER,
        customer_id     INTEGER,
        invoice_number  TEXT UNIQUE,
        invoice_date    TEXT NOT NULL,
        due_date        TEXT NOT NULL,
        total_amount    REAL NOT NULL,
        status          TEXT CHECK (status IN ('draft','sent','paid','overdue','cancelled')),
        notes           TEXT,
        FOREIGN KEY (project_id)  REFERENCES Project(project_id)   ON DELETE SET NULL,
        FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS User (
        user_id               INTEGER PRIMARY KEY AUTOINCREMENT,
        username              TEXT NOT NULL UNIQUE,
        password_hash         TEXT NOT NULL,
        password_salt         TEXT NOT NULL,
        role                  TEXT NOT NULL CHECK (role IN
                                ('admin','project_manager','member','viewer')),
        employee_id           INTEGER,
        is_active             INTEGER NOT NULL DEFAULT 1,
        must_change_password  INTEGER NOT NULL DEFAULT 0,
        created_at            TEXT NOT NULL,
        last_login_at         TEXT,
        FOREIGN KEY (employee_id) REFERENCES Employee(employee_id)
            ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS User_Project_Access (
        access_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id        INTEGER NOT NULL,
        project_id     INTEGER NOT NULL,
        project_role   TEXT NOT NULL CHECK (project_role IN
                            ('project_manager','member','viewer')),
        granted_at     TEXT NOT NULL,
        FOREIGN KEY (user_id)    REFERENCES User(user_id)       ON DELETE CASCADE,
        FOREIGN KEY (project_id) REFERENCES Project(project_id) ON DELETE CASCADE,
        UNIQUE (user_id, project_id)
    )
    """,
]


INDEX_STATEMENTS = [
    "CREATE INDEX IF NOT EXISTS idx_employee_department ON Employee(department_id)",
    "CREATE INDEX IF NOT EXISTS idx_project_customer    ON Project(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_task_project        ON Task(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_assignment_project  ON Project_Assignment(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_assignment_employee ON Project_Assignment(employee_id)",
    "CREATE INDEX IF NOT EXISTS idx_assignment_external ON Project_Assignment(external_id)",
    "CREATE INDEX IF NOT EXISTS idx_time_task           ON Time_Entry(task_id)",
    "CREATE INDEX IF NOT EXISTS idx_risk_project        ON Project_Risk(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_invoice_project     ON Invoice(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_invoice_customer    ON Invoice(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_empknow_employee    ON Employee_Knowledge(employee_id)",
    "CREATE INDEX IF NOT EXISTS idx_empknow_knowledge   ON Employee_Knowledge(knowledge_id)",
    "CREATE INDEX IF NOT EXISTS idx_user_employee       ON User(employee_id)",
    "CREATE INDEX IF NOT EXISTS idx_upa_user            ON User_Project_Access(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_upa_project         ON User_Project_Access(project_id)",
]


TABLES_IN_DEPENDENCY_ORDER = [
    'Department',
    'Employee',
    'External_Resource',
    'Customer',
    'Knowledge',
    'Project',
    'Task',
    'Project_Assignment',
    'Employee_Knowledge',
    'Time_Entry',
    'Project_Risk',
    'Invoice',
    'User',
    'User_Project_Access',
]

# Tables that hold project-management *data* (not auth). Used by import_excel
# and by reset_database when we want to wipe data without dropping the User
# accounts.
DATA_TABLES_IN_DEPENDENCY_ORDER = [
    t for t in TABLES_IN_DEPENDENCY_ORDER
    if t not in ('User', 'User_Project_Access')
]


def init_database():
    """Create all tables and indexes if they do not already exist."""
    with get_connection() as conn:
        cur = conn.cursor()
        for stmt in SCHEMA_STATEMENTS:
            cur.execute(stmt)
        for stmt in INDEX_STATEMENTS:
            cur.execute(stmt)


def reset_database(*, include_users=False):
    """Drop the project-management tables and recreate them empty.

    By default ``User`` and ``User_Project_Access`` are preserved so a data
    reload from Excel does NOT wipe out the people who can log in. Pass
    ``include_users=True`` to nuke everything (used only by tests).
    """
    tables = TABLES_IN_DEPENDENCY_ORDER if include_users else DATA_TABLES_IN_DEPENDENCY_ORDER
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = OFF")
        for tbl in reversed(tables):
            cur.execute(f"DROP TABLE IF EXISTS {tbl}")
        cur.execute("PRAGMA foreign_keys = ON")
    init_database()


def table_counts():
    """Return a dict of {table_name: row_count} for all tables."""
    counts = {}
    with get_connection() as conn:
        cur = conn.cursor()
        for tbl in TABLES_IN_DEPENDENCY_ORDER:
            cur.execute(f"SELECT COUNT(*) AS n FROM {tbl}")
            counts[tbl] = cur.fetchone()['n']
    return counts


if __name__ == '__main__':
    init_database()
    print("Schema initialized at", DB_PATH)
    for t, n in table_counts().items():
        print(f"  {t:<22} {n} rows")
