"""Database engine + helpers shared by the web app.

Uses SQLAlchemy Core so the same code works against both SQLite (local dev)
and Postgres (AWS RDS). For a fresh DB it bootstraps the schema by
delegating to the existing legacy module ``database.py`` when on SQLite, or
runs the equivalent statements directly via SQLAlchemy when on Postgres.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from server.settings import DATABASE_URL


def _make_engine() -> Engine:
    kwargs: dict[str, Any] = {"future": True, "pool_pre_ping": True}
    if DATABASE_URL.startswith("sqlite"):
        # FK enforcement + thread safety for SQLite
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(DATABASE_URL, **kwargs)


engine: Engine = _make_engine()


@contextmanager
def conn():
    """Yield a connection inside an implicit transaction; commit on success."""
    with engine.begin() as c:
        if DATABASE_URL.startswith("sqlite"):
            c.exec_driver_sql("PRAGMA foreign_keys = ON")
        yield c


def fetch_all(sql: str, params: dict | None = None) -> list[dict]:
    with conn() as c:
        result = c.execute(text(sql), params or {})
        return [dict(r._mapping) for r in result]


def fetch_one(sql: str, params: dict | None = None) -> dict | None:
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: dict | None = None) -> Any:
    with conn() as c:
        return c.execute(text(sql), params or {})


def init_schema() -> None:
    """Create tables if they don't exist.

    For SQLite we reuse the existing legacy ``database.py``.
    For Postgres we run dedicated DDL that handles reserved words
    (quoting "User"), avoids circular FK issues by adding FK
    constraints after all tables exist, and maps types correctly.
    """
    if DATABASE_URL.startswith("sqlite"):
        import database as legacy
        legacy.init_database()
        return

    # ── Postgres DDL ──
    _PG_TABLES = [
        # 1. Department (no FK to Employee yet — added later)
        """CREATE TABLE IF NOT EXISTS "Department" (
            department_id        SERIAL PRIMARY KEY,
            department_name      TEXT NOT NULL,
            manager_employee_id  INTEGER,
            cost_center          TEXT UNIQUE,
            status               TEXT CHECK (status IN ('active','inactive')),
            created_at           TEXT NOT NULL
        )""",
        # 2. Employee
        """CREATE TABLE IF NOT EXISTS "Employee" (
            employee_id    SERIAL PRIMARY KEY,
            first_name     TEXT NOT NULL,
            last_name      TEXT NOT NULL,
            employee_code  TEXT UNIQUE,
            email          TEXT UNIQUE,
            phone          TEXT,
            role           TEXT NOT NULL,
            department_id  INTEGER REFERENCES "Department"(department_id) ON DELETE SET NULL,
            hourly_rate    NUMERIC NOT NULL,
            hire_date      TEXT NOT NULL,
            status         TEXT CHECK (status IN ('active','inactive')),
            created_at     TEXT NOT NULL
        )""",
        # 3. External_Resource
        """CREATE TABLE IF NOT EXISTS "External_Resource" (
            external_id     SERIAL PRIMARY KEY,
            first_name      TEXT NOT NULL,
            last_name       TEXT NOT NULL,
            company         TEXT,
            email           TEXT UNIQUE,
            phone           TEXT,
            hourly_rate     NUMERIC NOT NULL,
            contract_type   TEXT CHECK (contract_type IN ('freelancer','outsource','consultant')),
            specialty       TEXT,
            status          TEXT CHECK (status IN ('active','inactive')),
            contract_start  TEXT NOT NULL,
            contract_end    TEXT,
            created_at      TEXT NOT NULL
        )""",
        # 4. Customer
        """CREATE TABLE IF NOT EXISTS "Customer" (
            customer_id    SERIAL PRIMARY KEY,
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
        )""",
        # 5. Knowledge
        """CREATE TABLE IF NOT EXISTS "Knowledge" (
            knowledge_id  SERIAL PRIMARY KEY,
            subject       TEXT NOT NULL,
            category      TEXT CHECK (category IN
                            ('Frontend','Backend','Design','DevOps','PM','QA','Data','Mobile')),
            description   TEXT
        )""",
        # 6. Project
        """CREATE TABLE IF NOT EXISTS "Project" (
            project_id       SERIAL PRIMARY KEY,
            project_name     TEXT NOT NULL,
            project_code     TEXT UNIQUE,
            customer_id      INTEGER REFERENCES "Customer"(customer_id) ON DELETE SET NULL,
            description      TEXT,
            status           TEXT CHECK (status IN
                                ('planning','in_progress','on_hold','completed','cancelled')),
            priority         TEXT CHECK (priority IN ('low','medium','high','critical')),
            estimated_hours  NUMERIC,
            actual_hours     NUMERIC,
            budget           NUMERIC,
            actual_cost      NUMERIC,
            start_date       TEXT,
            end_date         TEXT,
            created_at       TEXT NOT NULL
        )""",
        # 7. Task
        """CREATE TABLE IF NOT EXISTS "Task" (
            task_id               SERIAL PRIMARY KEY,
            project_id            INTEGER NOT NULL REFERENCES "Project"(project_id) ON DELETE CASCADE,
            title                 TEXT NOT NULL,
            description           TEXT,
            assigned_employee_id  INTEGER REFERENCES "Employee"(employee_id) ON DELETE SET NULL,
            assigned_external_id  INTEGER REFERENCES "External_Resource"(external_id) ON DELETE SET NULL,
            status                TEXT CHECK (status IN
                                    ('todo','in_progress','in_review','done','blocked')),
            priority              TEXT CHECK (priority IN ('low','medium','high','critical')),
            estimated_hours       NUMERIC,
            actual_hours          NUMERIC,
            due_date              TEXT,
            completed_date        TEXT,
            created_at            TEXT NOT NULL,
            CHECK (
                (assigned_employee_id IS NOT NULL AND assigned_external_id IS NULL)
             OR (assigned_employee_id IS NULL     AND assigned_external_id IS NOT NULL)
             OR (assigned_employee_id IS NULL     AND assigned_external_id IS NULL)
            )
        )""",
        # 8. Project_Assignment
        """CREATE TABLE IF NOT EXISTS "Project_Assignment" (
            assignment_id    SERIAL PRIMARY KEY,
            project_id       INTEGER NOT NULL REFERENCES "Project"(project_id) ON DELETE CASCADE,
            employee_id      INTEGER REFERENCES "Employee"(employee_id) ON DELETE SET NULL,
            external_id      INTEGER REFERENCES "External_Resource"(external_id) ON DELETE SET NULL,
            role_in_project  TEXT,
            allocated_hours  NUMERIC,
            start_date       TEXT,
            end_date         TEXT,
            CHECK (
                (employee_id IS NOT NULL AND external_id IS NULL)
             OR (employee_id IS NULL     AND external_id IS NOT NULL)
            )
        )""",
        # 9. Employee_Knowledge
        """CREATE TABLE IF NOT EXISTS "Employee_Knowledge" (
            employee_knowledge_id  SERIAL PRIMARY KEY,
            employee_id            INTEGER NOT NULL REFERENCES "Employee"(employee_id) ON DELETE CASCADE,
            knowledge_id           INTEGER NOT NULL REFERENCES "Knowledge"(knowledge_id) ON DELETE CASCADE,
            years_experience       INTEGER,
            proficiency            TEXT CHECK (proficiency IN ('junior','mid','senior','expert')),
            UNIQUE (employee_id, knowledge_id)
        )""",
        # 10. Time_Entry
        """CREATE TABLE IF NOT EXISTS "Time_Entry" (
            time_entry_id  SERIAL PRIMARY KEY,
            task_id        INTEGER NOT NULL REFERENCES "Task"(task_id) ON DELETE CASCADE,
            employee_id    INTEGER REFERENCES "Employee"(employee_id) ON DELETE SET NULL,
            external_id    INTEGER REFERENCES "External_Resource"(external_id) ON DELETE SET NULL,
            date           TEXT NOT NULL,
            hours          NUMERIC NOT NULL,
            description    TEXT,
            billable       TEXT CHECK (billable IN ('yes','no')),
            CHECK (
                (employee_id IS NOT NULL AND external_id IS NULL)
             OR (employee_id IS NULL     AND external_id IS NOT NULL)
            )
        )""",
        # 11. Project_Risk
        """CREATE TABLE IF NOT EXISTS "Project_Risk" (
            risk_id          SERIAL PRIMARY KEY,
            project_id       INTEGER NOT NULL REFERENCES "Project"(project_id) ON DELETE CASCADE,
            description      TEXT NOT NULL,
            probability      TEXT CHECK (probability IN ('low','medium','high')),
            impact           TEXT CHECK (impact IN ('low','medium','high')),
            mitigation_plan  TEXT,
            status           TEXT CHECK (status IN ('identified','mitigating','resolved','accepted')),
            identified_date  TEXT
        )""",
        # 12. Invoice
        """CREATE TABLE IF NOT EXISTS "Invoice" (
            invoice_id      SERIAL PRIMARY KEY,
            project_id      INTEGER REFERENCES "Project"(project_id) ON DELETE SET NULL,
            customer_id     INTEGER REFERENCES "Customer"(customer_id) ON DELETE SET NULL,
            invoice_number  TEXT UNIQUE,
            invoice_date    TEXT NOT NULL,
            due_date        TEXT NOT NULL,
            total_amount    NUMERIC NOT NULL,
            status          TEXT CHECK (status IN ('draft','sent','paid','overdue','cancelled')),
            notes           TEXT
        )""",
        # 13. User (reserved word — must be quoted)
        """CREATE TABLE IF NOT EXISTS "User" (
            user_id               SERIAL PRIMARY KEY,
            username              TEXT NOT NULL UNIQUE,
            password_hash         TEXT NOT NULL,
            password_salt         TEXT NOT NULL,
            role                  TEXT NOT NULL CHECK (role IN
                                    ('admin','project_manager','member','viewer')),
            employee_id           INTEGER REFERENCES "Employee"(employee_id) ON DELETE SET NULL,
            is_active             INTEGER NOT NULL DEFAULT 1,
            must_change_password  INTEGER NOT NULL DEFAULT 0,
            created_at            TEXT NOT NULL,
            last_login_at         TEXT
        )""",
        # 14. User_Project_Access
        """CREATE TABLE IF NOT EXISTS "User_Project_Access" (
            access_id      SERIAL PRIMARY KEY,
            user_id        INTEGER NOT NULL REFERENCES "User"(user_id) ON DELETE CASCADE,
            project_id     INTEGER NOT NULL REFERENCES "Project"(project_id) ON DELETE CASCADE,
            project_role   TEXT NOT NULL CHECK (project_role IN
                                ('project_manager','member','viewer')),
            granted_at     TEXT NOT NULL,
            UNIQUE (user_id, project_id)
        )""",
    ]

    # Deferred FK: Department.manager_employee_id -> Employee
    _PG_DEFERRED_FK = """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_dept_manager'
            ) THEN
                ALTER TABLE "Department"
                    ADD CONSTRAINT fk_dept_manager
                    FOREIGN KEY (manager_employee_id)
                    REFERENCES "Employee"(employee_id) ON DELETE SET NULL;
            END IF;
        END $$
    """

    _PG_INDEXES = [
        'CREATE INDEX IF NOT EXISTS idx_employee_department ON "Employee"(department_id)',
        'CREATE INDEX IF NOT EXISTS idx_project_customer    ON "Project"(customer_id)',
        'CREATE INDEX IF NOT EXISTS idx_task_project        ON "Task"(project_id)',
        'CREATE INDEX IF NOT EXISTS idx_assignment_project  ON "Project_Assignment"(project_id)',
        'CREATE INDEX IF NOT EXISTS idx_assignment_employee ON "Project_Assignment"(employee_id)',
        'CREATE INDEX IF NOT EXISTS idx_assignment_external ON "Project_Assignment"(external_id)',
        'CREATE INDEX IF NOT EXISTS idx_time_task           ON "Time_Entry"(task_id)',
        'CREATE INDEX IF NOT EXISTS idx_risk_project        ON "Project_Risk"(project_id)',
        'CREATE INDEX IF NOT EXISTS idx_invoice_project     ON "Invoice"(project_id)',
        'CREATE INDEX IF NOT EXISTS idx_invoice_customer    ON "Invoice"(customer_id)',
        'CREATE INDEX IF NOT EXISTS idx_empknow_employee    ON "Employee_Knowledge"(employee_id)',
        'CREATE INDEX IF NOT EXISTS idx_empknow_knowledge   ON "Employee_Knowledge"(knowledge_id)',
        'CREATE INDEX IF NOT EXISTS idx_user_employee       ON "User"(employee_id)',
        'CREATE INDEX IF NOT EXISTS idx_upa_user            ON "User_Project_Access"(user_id)',
        'CREATE INDEX IF NOT EXISTS idx_upa_project         ON "User_Project_Access"(project_id)',
    ]

    with conn() as c:
        for ddl in _PG_TABLES:
            c.execute(text(ddl))
        c.execute(text(_PG_DEFERRED_FK))
        for idx in _PG_INDEXES:
            c.execute(text(idx))
