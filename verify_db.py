"""
Verification script for the Project Management database.

Reports:
  1. Row counts per table vs expected (from the original Excel sample).
  2. SQLite foreign-key integrity check.
  3. XOR rule for Project_Assignment / Time_Entry (employee_id XOR external_id
     must be set; for Task the rule is "at most one" — both null is allowed).
  4. A sanity SELECT joining Project + Customer.

Exits with status 0 on success, 1 on any failure.
"""

from __future__ import annotations

import sys

from database import get_connection, TABLES_IN_DEPENDENCY_ORDER

EXPECTED_ROW_COUNTS = {
    'Department':         8,
    'Employee':           15,
    'External_Resource':  8,
    'Customer':           8,
    'Knowledge':          20,
    'Project':            10,
    'Task':               30,
    'Project_Assignment': 32,
    'Employee_Knowledge': 38,
    'Time_Entry':         40,
    'Project_Risk':       10,
    'Invoice':            12,
}


def check_row_counts():
    print("━" * 60)
    print("1. Row counts")
    print("━" * 60)
    failures = []
    with get_connection() as conn:
        cur = conn.cursor()
        for tbl in TABLES_IN_DEPENDENCY_ORDER:
            cur.execute(f"SELECT COUNT(*) AS n FROM {tbl}")
            n = cur.fetchone()['n']
            expected = EXPECTED_ROW_COUNTS[tbl]
            mark = '✓' if n == expected else '✗'
            print(f"  {mark} {tbl:<22} {n:>3} rows  (expected {expected})")
            if n != expected:
                failures.append((tbl, n, expected))
    return failures


def check_fk_integrity():
    print()
    print("━" * 60)
    print("2. Foreign-key integrity")
    print("━" * 60)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_key_check")
        rows = cur.fetchall()
    if rows:
        print(f"  ✗ {len(rows)} violation(s):")
        for r in rows[:10]:
            print(f"    {dict(r)}")
        return rows
    print("  ✓ No foreign-key violations.")
    return []


def check_xor_rule():
    print()
    print("━" * 60)
    print("3. employee_id XOR external_id rule")
    print("━" * 60)
    failures = []
    with get_connection() as conn:
        cur = conn.cursor()

        # Project_Assignment: exactly one must be set
        cur.execute("""
            SELECT COUNT(*) AS n FROM Project_Assignment
            WHERE NOT (
                (employee_id IS NOT NULL AND external_id IS NULL) OR
                (employee_id IS NULL     AND external_id IS NOT NULL)
            )
        """)
        n = cur.fetchone()['n']
        mark = '✓' if n == 0 else '✗'
        print(f"  {mark} Project_Assignment violations:  {n}")
        if n: failures.append(('Project_Assignment', n))

        # Time_Entry: exactly one must be set
        cur.execute("""
            SELECT COUNT(*) AS n FROM Time_Entry
            WHERE NOT (
                (employee_id IS NOT NULL AND external_id IS NULL) OR
                (employee_id IS NULL     AND external_id IS NOT NULL)
            )
        """)
        n = cur.fetchone()['n']
        mark = '✓' if n == 0 else '✗'
        print(f"  {mark} Time_Entry violations:          {n}")
        if n: failures.append(('Time_Entry', n))

        # Task: at most one assignee (both NULL is OK — task unassigned)
        cur.execute("""
            SELECT COUNT(*) AS n FROM Task
            WHERE assigned_employee_id IS NOT NULL
              AND assigned_external_id IS NOT NULL
        """)
        n = cur.fetchone()['n']
        mark = '✓' if n == 0 else '✗'
        print(f"  {mark} Task double-assignment cases:    {n}")
        if n: failures.append(('Task', n))

    return failures


def sanity_join():
    print()
    print("━" * 60)
    print("4. Sanity join — projects with their customers")
    print("━" * 60)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                p.project_code,
                p.project_name,
                p.status,
                p.priority,
                c.customer_name,
                p.budget,
                ROUND(100.0 * COALESCE(p.actual_cost,0) / NULLIF(p.budget,0), 1) AS pct_spent
            FROM Project p
            LEFT JOIN Customer c ON c.customer_id = p.customer_id
            ORDER BY p.project_code
        """)
        rows = cur.fetchall()
    print(f"  {'Code':<8} {'Status':<12} {'Priority':<9} {'Customer':<28} "
          f"{'Budget':>10} {'%Spent':>7}")
    for r in rows:
        print(f"  {r['project_code']:<8} {r['status']:<12} {r['priority']:<9} "
              f"{(r['customer_name'] or '-'):<28} "
              f"{(r['budget'] or 0):>10,.0f} "
              f"{(r['pct_spent'] if r['pct_spent'] is not None else 0):>6}%")
    return rows


def main():
    fail_counts = check_row_counts()
    fail_fks    = check_fk_integrity()
    fail_xor    = check_xor_rule()
    rows        = sanity_join()

    print()
    print("━" * 60)
    print("Summary")
    print("━" * 60)
    if not fail_counts and not fail_fks and not fail_xor and rows:
        print("✓ All checks passed.")
        return 0
    if fail_counts:
        print(f"✗ Row-count mismatches: {len(fail_counts)}")
    if fail_fks:
        print(f"✗ FK violations: {len(fail_fks)}")
    if fail_xor:
        print(f"✗ XOR rule failures: {len(fail_xor)}")
    return 1


if __name__ == '__main__':
    sys.exit(main())
