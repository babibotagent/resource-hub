"""Web-adapted CRUD configurations. Same structure as views/crud_configs.py
but FK lookups use server.db instead of the legacy sqlite3 connection."""
from __future__ import annotations

from server.db import fetch_all


# ---------------------------------------------------------------------------
# FK lookup helpers
# ---------------------------------------------------------------------------
def _fk_lookup(sql: str) -> callable:
    """Return a callable that fetches (id, label) pairs."""
    def _fn():
        rows = fetch_all(sql)
        return [(r["id"], r["lbl"]) for r in rows]
    return _fn


customers_lookup = _fk_lookup(
    "SELECT customer_id AS id, customer_name || ' (' || COALESCE(customer_code,'') || ')' AS lbl "
    "FROM Customer ORDER BY customer_name")

projects_lookup = _fk_lookup(
    "SELECT project_id AS id, COALESCE(project_code,'') || ' - ' || project_name AS lbl "
    "FROM Project ORDER BY project_code")

employees_lookup = _fk_lookup(
    "SELECT employee_id AS id, first_name || ' ' || last_name AS lbl "
    "FROM Employee WHERE status = 'active' ORDER BY first_name")

externals_lookup = _fk_lookup(
    "SELECT external_id AS id, first_name || ' ' || last_name || ' (' || COALESCE(company,'') || ')' AS lbl "
    "FROM External_Resource WHERE status = 'active' ORDER BY first_name")

departments_lookup = _fk_lookup(
    "SELECT department_id AS id, department_name AS lbl FROM Department ORDER BY department_name")

knowledge_lookup = _fk_lookup(
    "SELECT knowledge_id AS id, subject || ' (' || COALESCE(category,'') || ')' AS lbl "
    "FROM Knowledge ORDER BY subject")

tasks_lookup = _fk_lookup(
    "SELECT task_id AS id, title || ' [' || COALESCE(status,'') || ']' AS lbl "
    "FROM Task ORDER BY task_id DESC")


# ---------------------------------------------------------------------------
# Enum values (must match CHECK constraints in database.py)
# ---------------------------------------------------------------------------
STATUS_ACTIVE   = ['active', 'inactive']
PROJECT_STATUS  = ['planning', 'in_progress', 'on_hold', 'completed', 'cancelled']
PRIORITY        = ['low', 'medium', 'high', 'critical']
TASK_STATUS     = ['todo', 'in_progress', 'in_review', 'done', 'blocked']
KNOWLEDGE_CAT   = ['Frontend', 'Backend', 'Design', 'DevOps', 'PM', 'QA', 'Data', 'Mobile']
CONTRACT_TYPES  = ['freelancer', 'outsource', 'consultant']
PAYMENT_TERMS   = ['NET30', 'NET60', 'NET90']
PROB_IMPACT     = ['low', 'medium', 'high']
RISK_STATUS     = ['identified', 'mitigating', 'resolved', 'accepted']
INVOICE_STATUS  = ['draft', 'sent', 'paid', 'overdue', 'cancelled']
BILLABLE        = ['yes', 'no']
USER_ROLES      = ['admin', 'project_manager', 'member', 'viewer']


# ---------------------------------------------------------------------------
# Table configurations
# ---------------------------------------------------------------------------
CUSTOMER = {
    'table': 'Customer', 'pk': 'customer_id', 'singular': 'customer',
    'title': 'Customers', 'subtitle': 'Manage clients and accounts',
    'list_sql': "SELECT * FROM Customer",
    'list_order': "ORDER BY customer_name",
    'columns': [
        {'key': 'customer_id',   'header': 'ID'},
        {'key': 'customer_code', 'header': 'Code'},
        {'key': 'customer_name', 'header': 'Name'},
        {'key': 'contact_name',  'header': 'Contact'},
        {'key': 'industry',      'header': 'Industry'},
        {'key': 'payment_terms', 'header': 'Terms'},
        {'key': 'status',        'header': 'Status'},
    ],
    'form_fields': [
        {'key': 'customer_name', 'label': 'Name', 'type': 'text', 'required': True},
        {'key': 'customer_code', 'label': 'Code (CLI-XXX)', 'type': 'text'},
        {'key': 'contact_name',  'label': 'Contact name', 'type': 'text'},
        {'key': 'contact_email', 'label': 'Contact email', 'type': 'text'},
        {'key': 'contact_phone', 'label': 'Contact phone', 'type': 'text'},
        {'key': 'industry',      'label': 'Industry', 'type': 'text'},
        {'key': 'address',       'label': 'Address', 'type': 'text'},
        {'key': 'country',       'label': 'Country', 'type': 'text'},
        {'key': 'payment_terms', 'label': 'Payment terms', 'type': 'enum', 'values': PAYMENT_TERMS, 'default': 'NET30'},
        {'key': 'status',        'label': 'Status', 'type': 'enum', 'values': STATUS_ACTIVE, 'default': 'active'},
    ],
    'auto_now': ['created_at'],
}

EMPLOYEE = {
    'table': 'Employee', 'pk': 'employee_id', 'singular': 'employee',
    'title': 'Employees', 'subtitle': 'Internal team members',
    'list_sql': """SELECT e.*, d.department_name FROM Employee e
                   LEFT JOIN Department d ON d.department_id = e.department_id""",
    'list_order': "ORDER BY e.first_name, e.last_name",
    'columns': [
        {'key': 'employee_id',    'header': 'ID'},
        {'key': 'employee_code',  'header': 'Code'},
        {'key': 'first_name',     'header': 'First name'},
        {'key': 'last_name',      'header': 'Last name'},
        {'key': 'role',           'header': 'Role'},
        {'key': 'department_name','header': 'Department'},
        {'key': 'email',          'header': 'Email'},
        {'key': 'hourly_rate',    'header': 'Rate'},
        {'key': 'status',         'header': 'Status'},
    ],
    'form_fields': [
        {'key': 'first_name',    'label': 'First name', 'type': 'text', 'required': True},
        {'key': 'last_name',     'label': 'Last name', 'type': 'text', 'required': True},
        {'key': 'employee_code', 'label': 'Code (EMP-XXX)', 'type': 'text'},
        {'key': 'email',         'label': 'Email', 'type': 'text'},
        {'key': 'phone',         'label': 'Phone', 'type': 'text'},
        {'key': 'role',          'label': 'Role / Job title', 'type': 'text', 'required': True},
        {'key': 'department_id', 'label': 'Department', 'type': 'fk', 'choices_fn': departments_lookup, 'nullable': True},
        {'key': 'hourly_rate',   'label': 'Hourly rate (EUR)', 'type': 'real', 'required': True},
        {'key': 'hire_date',     'label': 'Hire date', 'type': 'date', 'required': True},
        {'key': 'status',        'label': 'Status', 'type': 'enum', 'values': STATUS_ACTIVE, 'default': 'active'},
    ],
    'auto_now': ['created_at'],
}

EXTERNAL = {
    'table': 'External_Resource', 'pk': 'external_id', 'singular': 'external resource',
    'title': 'External Resources', 'subtitle': 'Freelancers, contractors, consultants',
    'list_sql': "SELECT * FROM External_Resource",
    'list_order': "ORDER BY first_name",
    'columns': [
        {'key': 'external_id',  'header': 'ID'},
        {'key': 'first_name',   'header': 'First'},
        {'key': 'last_name',    'header': 'Last'},
        {'key': 'company',      'header': 'Company'},
        {'key': 'specialty',    'header': 'Specialty'},
        {'key': 'contract_type','header': 'Type'},
        {'key': 'hourly_rate',  'header': 'Rate'},
        {'key': 'status',       'header': 'Status'},
    ],
    'form_fields': [
        {'key': 'first_name',    'label': 'First name', 'type': 'text', 'required': True},
        {'key': 'last_name',     'label': 'Last name', 'type': 'text', 'required': True},
        {'key': 'company',       'label': 'Company', 'type': 'text'},
        {'key': 'email',         'label': 'Email', 'type': 'text'},
        {'key': 'phone',         'label': 'Phone', 'type': 'text'},
        {'key': 'hourly_rate',   'label': 'Hourly rate (EUR)', 'type': 'real', 'required': True},
        {'key': 'contract_type', 'label': 'Contract type', 'type': 'enum', 'values': CONTRACT_TYPES, 'default': 'freelancer'},
        {'key': 'specialty',     'label': 'Specialty', 'type': 'text'},
        {'key': 'contract_start','label': 'Contract start', 'type': 'date', 'required': True},
        {'key': 'contract_end',  'label': 'Contract end', 'type': 'date'},
        {'key': 'status',        'label': 'Status', 'type': 'enum', 'values': STATUS_ACTIVE, 'default': 'active'},
    ],
    'auto_now': ['created_at'],
}

DEPARTMENT = {
    'table': 'Department', 'pk': 'department_id', 'singular': 'department',
    'title': 'Departments', 'subtitle': 'Organizational units',
    'list_sql': """SELECT d.*, COALESCE(e.first_name || ' ' || e.last_name, '') AS manager_name
                   FROM Department d
                   LEFT JOIN Employee e ON e.employee_id = d.manager_employee_id""",
    'list_order': "ORDER BY d.department_name",
    'columns': [
        {'key': 'department_id',   'header': 'ID'},
        {'key': 'department_name', 'header': 'Name'},
        {'key': 'manager_name',    'header': 'Manager'},
        {'key': 'cost_center',     'header': 'Cost center'},
        {'key': 'status',          'header': 'Status'},
    ],
    'form_fields': [
        {'key': 'department_name',     'label': 'Name', 'type': 'text', 'required': True},
        {'key': 'manager_employee_id', 'label': 'Manager', 'type': 'fk', 'choices_fn': employees_lookup, 'nullable': True},
        {'key': 'cost_center',         'label': 'Cost center', 'type': 'text'},
        {'key': 'status',              'label': 'Status', 'type': 'enum', 'values': STATUS_ACTIVE, 'default': 'active'},
    ],
    'auto_now': ['created_at'],
}

KNOWLEDGE = {
    'table': 'Knowledge', 'pk': 'knowledge_id', 'singular': 'skill',
    'title': 'Skills / Knowledge', 'subtitle': 'Catalogue of competencies',
    'list_sql': "SELECT * FROM Knowledge",
    'list_order': "ORDER BY category, subject",
    'columns': [
        {'key': 'knowledge_id', 'header': 'ID'},
        {'key': 'category',     'header': 'Category'},
        {'key': 'subject',      'header': 'Subject'},
        {'key': 'description',  'header': 'Description'},
    ],
    'form_fields': [
        {'key': 'subject',     'label': 'Subject', 'type': 'text', 'required': True},
        {'key': 'category',    'label': 'Category', 'type': 'enum', 'values': KNOWLEDGE_CAT, 'default': 'Frontend'},
        {'key': 'description', 'label': 'Description', 'type': 'textarea'},
    ],
}

PROJECT = {
    'table': 'Project', 'pk': 'project_id', 'singular': 'project',
    'title': 'Projects', 'subtitle': 'Project portfolio',
    'list_sql': """SELECT p.*, c.customer_name FROM Project p
                   LEFT JOIN Customer c ON c.customer_id = p.customer_id""",
    'list_order': "ORDER BY p.start_date DESC, p.project_code",
    'columns': [
        {'key': 'project_id',   'header': 'ID'},
        {'key': 'project_code', 'header': 'Code'},
        {'key': 'project_name', 'header': 'Name'},
        {'key': 'customer_name','header': 'Customer'},
        {'key': 'status',       'header': 'Status'},
        {'key': 'priority',     'header': 'Priority'},
        {'key': 'budget',       'header': 'Budget'},
        {'key': 'actual_cost',  'header': 'Actual'},
        {'key': 'start_date',   'header': 'Start'},
        {'key': 'end_date',     'header': 'End'},
    ],
    'form_fields': [
        {'key': 'project_name',    'label': 'Name', 'type': 'text', 'required': True},
        {'key': 'project_code',    'label': 'Code (PRJ-XXX)', 'type': 'text'},
        {'key': 'customer_id',     'label': 'Customer', 'type': 'fk', 'choices_fn': customers_lookup, 'nullable': True},
        {'key': 'description',     'label': 'Description', 'type': 'textarea'},
        {'key': 'status',          'label': 'Status', 'type': 'enum', 'values': PROJECT_STATUS, 'default': 'planning'},
        {'key': 'priority',        'label': 'Priority', 'type': 'enum', 'values': PRIORITY, 'default': 'medium'},
        {'key': 'estimated_hours', 'label': 'Estimated hours', 'type': 'real'},
        {'key': 'actual_hours',    'label': 'Actual hours', 'type': 'real'},
        {'key': 'budget',          'label': 'Budget (EUR)', 'type': 'real'},
        {'key': 'actual_cost',     'label': 'Actual cost (EUR)', 'type': 'real'},
        {'key': 'start_date',      'label': 'Start date', 'type': 'date'},
        {'key': 'end_date',        'label': 'End date', 'type': 'date'},
    ],
    'auto_now': ['created_at'],
}

TASK = {
    'table': 'Task', 'pk': 'task_id', 'singular': 'task',
    'title': 'Tasks', 'subtitle': 'Work items across projects',
    'list_sql': """SELECT t.*, p.project_code, p.project_name,
                          COALESCE(e.first_name || ' ' || e.last_name,
                                   x.first_name || ' ' || x.last_name, '') AS assignee
                   FROM Task t
                   LEFT JOIN Project p ON p.project_id = t.project_id
                   LEFT JOIN Employee e ON e.employee_id = t.assigned_employee_id
                   LEFT JOIN External_Resource x ON x.external_id = t.assigned_external_id""",
    'list_order': "ORDER BY t.due_date, t.task_id DESC",
    'columns': [
        {'key': 'task_id',       'header': 'ID'},
        {'key': 'project_code',  'header': 'Project'},
        {'key': 'title',         'header': 'Title'},
        {'key': 'assignee',      'header': 'Assignee'},
        {'key': 'status',        'header': 'Status'},
        {'key': 'priority',      'header': 'Priority'},
        {'key': 'due_date',      'header': 'Due'},
        {'key': 'estimated_hours','header': 'Est.'},
        {'key': 'actual_hours',   'header': 'Actual'},
    ],
    'form_fields': [
        {'key': 'project_id',           'label': 'Project', 'type': 'fk', 'choices_fn': projects_lookup, 'required': True},
        {'key': 'title',                'label': 'Title', 'type': 'text', 'required': True},
        {'key': 'description',          'label': 'Description', 'type': 'textarea'},
        {'key': 'assigned_employee_id', 'label': 'Assignee (employee)', 'type': 'fk', 'choices_fn': employees_lookup, 'nullable': True},
        {'key': 'assigned_external_id', 'label': 'Assignee (external)', 'type': 'fk', 'choices_fn': externals_lookup, 'nullable': True},
        {'key': 'status',         'label': 'Status', 'type': 'enum', 'values': TASK_STATUS, 'default': 'todo'},
        {'key': 'priority',       'label': 'Priority', 'type': 'enum', 'values': PRIORITY, 'default': 'medium'},
        {'key': 'estimated_hours','label': 'Estimated hours', 'type': 'real'},
        {'key': 'actual_hours',   'label': 'Actual hours', 'type': 'real'},
        {'key': 'due_date',       'label': 'Due date', 'type': 'date'},
        {'key': 'completed_date', 'label': 'Completed date', 'type': 'date'},
    ],
    'auto_now': ['created_at'],
}

ASSIGNMENT = {
    'table': 'Project_Assignment', 'pk': 'assignment_id', 'singular': 'assignment',
    'title': 'Assignments', 'subtitle': 'Resource allocations to projects',
    'list_sql': """SELECT a.*, p.project_code, p.project_name,
                          COALESCE(e.first_name || ' ' || e.last_name,
                                   x.first_name || ' ' || x.last_name, '') AS person,
                          CASE WHEN a.employee_id IS NOT NULL THEN 'internal' ELSE 'external' END AS kind
                   FROM Project_Assignment a
                   LEFT JOIN Project p ON p.project_id = a.project_id
                   LEFT JOIN Employee e ON e.employee_id = a.employee_id
                   LEFT JOIN External_Resource x ON x.external_id = a.external_id""",
    'list_order': "ORDER BY a.start_date DESC",
    'columns': [
        {'key': 'assignment_id',  'header': 'ID'},
        {'key': 'project_code',   'header': 'Project'},
        {'key': 'person',         'header': 'Person'},
        {'key': 'kind',           'header': 'Type'},
        {'key': 'role_in_project','header': 'Role'},
        {'key': 'allocated_hours','header': 'Hours'},
        {'key': 'start_date',     'header': 'Start'},
        {'key': 'end_date',       'header': 'End'},
    ],
    'form_fields': [
        {'key': 'project_id',      'label': 'Project', 'type': 'fk', 'choices_fn': projects_lookup, 'required': True},
        {'key': 'employee_id',     'label': 'Employee (pick ONE)', 'type': 'fk', 'choices_fn': employees_lookup, 'nullable': True},
        {'key': 'external_id',     'label': 'External resource', 'type': 'fk', 'choices_fn': externals_lookup, 'nullable': True},
        {'key': 'role_in_project', 'label': 'Role in project', 'type': 'text'},
        {'key': 'allocated_hours', 'label': 'Allocated hours', 'type': 'real'},
        {'key': 'start_date',      'label': 'Start date', 'type': 'date'},
        {'key': 'end_date',        'label': 'End date', 'type': 'date'},
    ],
}

TIME_ENTRY = {
    'table': 'Time_Entry', 'pk': 'time_entry_id', 'singular': 'time entry',
    'title': 'Time Entries', 'subtitle': 'Hours logged against tasks',
    'list_sql': """SELECT te.*, t.title AS task_title, p.project_code,
                          COALESCE(e.first_name || ' ' || e.last_name,
                                   x.first_name || ' ' || x.last_name, '') AS person
                   FROM Time_Entry te
                   LEFT JOIN Task t ON t.task_id = te.task_id
                   LEFT JOIN Project p ON p.project_id = t.project_id
                   LEFT JOIN Employee e ON e.employee_id = te.employee_id
                   LEFT JOIN External_Resource x ON x.external_id = te.external_id""",
    'list_order': "ORDER BY te.date DESC, te.time_entry_id DESC",
    'columns': [
        {'key': 'time_entry_id', 'header': 'ID'},
        {'key': 'date',          'header': 'Date'},
        {'key': 'project_code',  'header': 'Project'},
        {'key': 'task_title',    'header': 'Task'},
        {'key': 'person',        'header': 'Person'},
        {'key': 'hours',         'header': 'Hours'},
        {'key': 'billable',      'header': 'Billable'},
        {'key': 'description',   'header': 'Description'},
    ],
    'form_fields': [
        {'key': 'task_id',     'label': 'Task', 'type': 'fk', 'choices_fn': tasks_lookup, 'required': True},
        {'key': 'employee_id', 'label': 'Employee (pick ONE)', 'type': 'fk', 'choices_fn': employees_lookup, 'nullable': True},
        {'key': 'external_id', 'label': 'External resource', 'type': 'fk', 'choices_fn': externals_lookup, 'nullable': True},
        {'key': 'date',        'label': 'Date', 'type': 'date', 'required': True},
        {'key': 'hours',       'label': 'Hours', 'type': 'real', 'required': True},
        {'key': 'description', 'label': 'Description', 'type': 'textarea'},
        {'key': 'billable',    'label': 'Billable', 'type': 'enum', 'values': BILLABLE, 'default': 'yes'},
    ],
}

RISK = {
    'table': 'Project_Risk', 'pk': 'risk_id', 'singular': 'risk',
    'title': 'Risks', 'subtitle': 'Project risk register',
    'list_sql': """SELECT r.*, p.project_code, p.project_name FROM Project_Risk r
                   LEFT JOIN Project p ON p.project_id = r.project_id""",
    'list_order': "ORDER BY r.identified_date DESC, r.risk_id DESC",
    'columns': [
        {'key': 'risk_id',         'header': 'ID'},
        {'key': 'project_code',    'header': 'Project'},
        {'key': 'description',     'header': 'Description'},
        {'key': 'probability',     'header': 'Prob.'},
        {'key': 'impact',          'header': 'Impact'},
        {'key': 'status',          'header': 'Status'},
        {'key': 'identified_date', 'header': 'Identified'},
    ],
    'form_fields': [
        {'key': 'project_id',      'label': 'Project', 'type': 'fk', 'choices_fn': projects_lookup, 'required': True},
        {'key': 'description',     'label': 'Description', 'type': 'textarea', 'required': True},
        {'key': 'probability',     'label': 'Probability', 'type': 'enum', 'values': PROB_IMPACT, 'default': 'medium'},
        {'key': 'impact',          'label': 'Impact', 'type': 'enum', 'values': PROB_IMPACT, 'default': 'medium'},
        {'key': 'mitigation_plan', 'label': 'Mitigation plan', 'type': 'textarea'},
        {'key': 'status',          'label': 'Status', 'type': 'enum', 'values': RISK_STATUS, 'default': 'identified'},
        {'key': 'identified_date', 'label': 'Identified date', 'type': 'date'},
    ],
}

INVOICE = {
    'table': 'Invoice', 'pk': 'invoice_id', 'singular': 'invoice',
    'title': 'Invoices', 'subtitle': 'Billing and revenue tracking',
    'list_sql': """SELECT i.*, p.project_code, c.customer_name FROM Invoice i
                   LEFT JOIN Project p ON p.project_id = i.project_id
                   LEFT JOIN Customer c ON c.customer_id = i.customer_id""",
    'list_order': "ORDER BY i.invoice_date DESC",
    'columns': [
        {'key': 'invoice_id',     'header': 'ID'},
        {'key': 'invoice_number', 'header': 'Number'},
        {'key': 'invoice_date',   'header': 'Date'},
        {'key': 'customer_name',  'header': 'Customer'},
        {'key': 'project_code',   'header': 'Project'},
        {'key': 'total_amount',   'header': 'Amount'},
        {'key': 'due_date',       'header': 'Due'},
        {'key': 'status',         'header': 'Status'},
    ],
    'form_fields': [
        {'key': 'invoice_number', 'label': 'Number (INV-YYYY-XXX)', 'type': 'text'},
        {'key': 'project_id',     'label': 'Project', 'type': 'fk', 'choices_fn': projects_lookup, 'nullable': True},
        {'key': 'customer_id',    'label': 'Customer', 'type': 'fk', 'choices_fn': customers_lookup, 'nullable': True},
        {'key': 'invoice_date',   'label': 'Invoice date', 'type': 'date', 'required': True},
        {'key': 'due_date',       'label': 'Due date', 'type': 'date', 'required': True},
        {'key': 'total_amount',   'label': 'Total amount (EUR)', 'type': 'real', 'required': True},
        {'key': 'status',         'label': 'Status', 'type': 'enum', 'values': INVOICE_STATUS, 'default': 'draft'},
        {'key': 'notes',          'label': 'Notes', 'type': 'textarea'},
    ],
}


# Map nav view_id -> config (matches sidebar links in base.html)
VIEW_CONFIGS: dict[str, dict] = {
    'projects':    PROJECT,
    'tasks':       TASK,
    'assignments': ASSIGNMENT,
    'timeentries': TIME_ENTRY,
    'risks':       RISK,
    'invoices':    INVOICE,
    'employees':   EMPLOYEE,
    'externals':   EXTERNAL,
    'customers':   CUSTOMER,
    'knowledge':   KNOWLEDGE,
    'departments': DEPARTMENT,
}
