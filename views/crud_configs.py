"""Per-table configuration dictionaries for the generic CrudView."""

from __future__ import annotations

from database import get_connection


def _money(v, _row=None):
    if v is None:
        return '-'
    try:
        return f"{float(v):,.2f}"
    except (TypeError, ValueError):
        return str(v)


def _none_dash(v, _row=None):
    return '-' if v in (None, '') else v


# ---------------------------------------------------------------------------
# Lookup helpers (FK choice loaders)
# ---------------------------------------------------------------------------
def _lookup(sql):
    def _fn():
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            return [(r[0], r[1]) for r in cur.fetchall()]
    return _fn


customers_lookup = _lookup(
    "SELECT customer_name || ' (' || COALESCE(customer_code,'') || ')' AS lbl, "
    "customer_id FROM Customer ORDER BY customer_name")

projects_lookup = _lookup(
    "SELECT COALESCE(project_code,'') || ' - ' || project_name AS lbl, project_id "
    "FROM Project ORDER BY project_code")

employees_lookup = _lookup(
    "SELECT first_name || ' ' || last_name AS lbl, employee_id "
    "FROM Employee WHERE status = 'active' ORDER BY first_name")

externals_lookup = _lookup(
    "SELECT first_name || ' ' || last_name || ' (' || COALESCE(company,'') || ')' AS lbl, external_id "
    "FROM External_Resource WHERE status = 'active' ORDER BY first_name")

departments_lookup = _lookup(
    "SELECT department_name, department_id FROM Department ORDER BY department_name")

knowledge_lookup = _lookup(
    "SELECT subject || ' (' || COALESCE(category,'') || ')' AS lbl, knowledge_id "
    "FROM Knowledge ORDER BY subject")

tasks_lookup = _lookup(
    "SELECT title || ' [' || COALESCE(status,'') || ']' AS lbl, task_id "
    "FROM Task ORDER BY task_id DESC")


# ---------------------------------------------------------------------------
# Enums (must match the CHECK constraints in database.py)
# ---------------------------------------------------------------------------
STATUS_ACTIVE   = ['active', 'inactive']
PROJECT_STATUS  = ['planning', 'in_progress', 'on_hold', 'completed', 'cancelled']
PRIORITY        = ['low', 'medium', 'high', 'critical']
TASK_STATUS     = ['todo', 'in_progress', 'in_review', 'done', 'blocked']
PROFICIENCY     = ['junior', 'mid', 'senior', 'expert']
KNOWLEDGE_CAT   = ['Frontend', 'Backend', 'Design', 'DevOps', 'PM', 'QA', 'Data', 'Mobile']
CONTRACT_TYPES  = ['freelancer', 'outsource', 'consultant']
PAYMENT_TERMS   = ['NET30', 'NET60', 'NET90']
PROB_IMPACT     = ['low', 'medium', 'high']
RISK_STATUS     = ['identified', 'mitigating', 'resolved', 'accepted']
INVOICE_STATUS  = ['draft', 'sent', 'paid', 'overdue', 'cancelled']
BILLABLE        = ['yes', 'no']


# ---------------------------------------------------------------------------
# Configurations
# ---------------------------------------------------------------------------
CUSTOMER = {
    'table': 'Customer', 'pk': 'customer_id', 'singular': 'customer',
    'title': 'Customers', 'subtitle': 'Manage clients and accounts',
    'edit_permission': 'customer.manage',
    'list_sql': "SELECT * FROM Customer WHERE 1=1",
    'list_order_by': "ORDER BY customer_name",
    'list_columns': [
        {'key': 'customer_id',   'header': 'ID',        'width': 50, 'anchor': 'center'},
        {'key': 'customer_code', 'header': 'Code',      'width': 90},
        {'key': 'customer_name', 'header': 'Name',      'width': 220},
        {'key': 'contact_name',  'header': 'Contact',   'width': 160, 'format': _none_dash},
        {'key': 'industry',      'header': 'Industry',  'width': 140, 'format': _none_dash},
        {'key': 'payment_terms', 'header': 'Terms',     'width': 80,  'anchor': 'center'},
        {'key': 'status',        'header': 'Status',    'width': 90,  'anchor': 'center'},
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
        {'key': 'payment_terms', 'label': 'Payment terms', 'type': 'enum',
         'values': PAYMENT_TERMS, 'default': 'NET30'},
        {'key': 'status',        'label': 'Status', 'type': 'enum',
         'values': STATUS_ACTIVE, 'default': 'active'},
    ],
    'auto_now_fields': ['created_at'],
}


EMPLOYEE = {
    'table': 'Employee', 'pk': 'employee_id', 'singular': 'employee',
    'title': 'Employees', 'subtitle': 'Internal team members',
    'edit_permission': 'employee.manage',
    'list_sql': """SELECT e.*, d.department_name FROM Employee e
                   LEFT JOIN Department d ON d.department_id = e.department_id
                   WHERE 1=1""",
    'list_order_by': "ORDER BY e.first_name, e.last_name",
    'list_columns': [
        {'key': 'employee_id',    'header': 'ID', 'width': 50, 'anchor': 'center'},
        {'key': 'employee_code',  'header': 'Code', 'width': 90},
        {'key': 'first_name',     'header': 'First name', 'width': 120},
        {'key': 'last_name',      'header': 'Last name', 'width': 120},
        {'key': 'role',           'header': 'Role', 'width': 160},
        {'key': 'department_name','header': 'Department', 'width': 140, 'format': _none_dash},
        {'key': 'email',          'header': 'Email', 'width': 220},
        {'key': 'hourly_rate',    'header': 'Rate', 'width': 80, 'anchor': 'e', 'format': _money},
        {'key': 'status',         'header': 'Status', 'width': 80, 'anchor': 'center'},
    ],
    'form_fields': [
        {'key': 'first_name',     'label': 'First name', 'type': 'text', 'required': True},
        {'key': 'last_name',      'label': 'Last name', 'type': 'text', 'required': True},
        {'key': 'employee_code',  'label': 'Code (EMP-XXX)', 'type': 'text'},
        {'key': 'email',          'label': 'Email', 'type': 'text'},
        {'key': 'phone',          'label': 'Phone', 'type': 'text'},
        {'key': 'role',           'label': 'Role / Job title', 'type': 'text', 'required': True},
        {'key': 'department_id',  'label': 'Department', 'type': 'fk',
         'choices_fn': departments_lookup, 'nullable': True},
        {'key': 'hourly_rate',    'label': 'Hourly rate (EUR)', 'type': 'real', 'required': True},
        {'key': 'hire_date',      'label': 'Hire date (YYYY-MM-DD)', 'type': 'date', 'required': True},
        {'key': 'status',         'label': 'Status', 'type': 'enum',
         'values': STATUS_ACTIVE, 'default': 'active'},
    ],
    'auto_now_fields': ['created_at'],
}


EXTERNAL = {
    'table': 'External_Resource', 'pk': 'external_id', 'singular': 'external resource',
    'title': 'External Resources', 'subtitle': 'Freelancers, contractors, consultants',
    'edit_permission': 'external.manage',
    'list_sql': "SELECT * FROM External_Resource WHERE 1=1",
    'list_order_by': "ORDER BY first_name",
    'list_columns': [
        {'key': 'external_id',  'header': 'ID', 'width': 50, 'anchor': 'center'},
        {'key': 'first_name',   'header': 'First', 'width': 110},
        {'key': 'last_name',    'header': 'Last', 'width': 110},
        {'key': 'company',      'header': 'Company', 'width': 160, 'format': _none_dash},
        {'key': 'specialty',    'header': 'Specialty', 'width': 160, 'format': _none_dash},
        {'key': 'contract_type','header': 'Type', 'width': 100, 'anchor': 'center'},
        {'key': 'hourly_rate',  'header': 'Rate', 'width': 80, 'anchor': 'e', 'format': _money},
        {'key': 'status',       'header': 'Status', 'width': 80, 'anchor': 'center'},
    ],
    'form_fields': [
        {'key': 'first_name',    'label': 'First name', 'type': 'text', 'required': True},
        {'key': 'last_name',     'label': 'Last name', 'type': 'text', 'required': True},
        {'key': 'company',       'label': 'Company', 'type': 'text'},
        {'key': 'email',         'label': 'Email', 'type': 'text'},
        {'key': 'phone',         'label': 'Phone', 'type': 'text'},
        {'key': 'hourly_rate',   'label': 'Hourly rate (EUR)', 'type': 'real', 'required': True},
        {'key': 'contract_type', 'label': 'Contract type', 'type': 'enum',
         'values': CONTRACT_TYPES, 'default': 'freelancer'},
        {'key': 'specialty',     'label': 'Specialty', 'type': 'text'},
        {'key': 'contract_start','label': 'Contract start (YYYY-MM-DD)', 'type': 'date', 'required': True},
        {'key': 'contract_end',  'label': 'Contract end (YYYY-MM-DD)', 'type': 'date'},
        {'key': 'status',        'label': 'Status', 'type': 'enum',
         'values': STATUS_ACTIVE, 'default': 'active'},
    ],
    'auto_now_fields': ['created_at'],
}


DEPARTMENT = {
    'table': 'Department', 'pk': 'department_id', 'singular': 'department',
    'title': 'Departments', 'subtitle': 'Organizational units',
    'edit_permission': 'department.manage',
    'list_sql': """SELECT d.*, COALESCE(e.first_name || ' ' || e.last_name, '-') AS manager_name
                   FROM Department d
                   LEFT JOIN Employee e ON e.employee_id = d.manager_employee_id
                   WHERE 1=1""",
    'list_order_by': "ORDER BY d.department_name",
    'list_columns': [
        {'key': 'department_id',   'header': 'ID', 'width': 50, 'anchor': 'center'},
        {'key': 'department_name', 'header': 'Name', 'width': 220},
        {'key': 'manager_name',    'header': 'Manager', 'width': 180},
        {'key': 'cost_center',     'header': 'Cost center', 'width': 120, 'format': _none_dash},
        {'key': 'status',          'header': 'Status', 'width': 90, 'anchor': 'center'},
    ],
    'form_fields': [
        {'key': 'department_name',     'label': 'Name', 'type': 'text', 'required': True},
        {'key': 'manager_employee_id', 'label': 'Manager', 'type': 'fk',
         'choices_fn': employees_lookup, 'nullable': True},
        {'key': 'cost_center',         'label': 'Cost center', 'type': 'text'},
        {'key': 'status',              'label': 'Status', 'type': 'enum',
         'values': STATUS_ACTIVE, 'default': 'active'},
    ],
    'auto_now_fields': ['created_at'],
}


KNOWLEDGE = {
    'table': 'Knowledge', 'pk': 'knowledge_id', 'singular': 'skill',
    'title': 'Skills / Knowledge', 'subtitle': 'Catalogue of competencies',
    'edit_permission': 'knowledge.manage',
    'list_sql': "SELECT * FROM Knowledge WHERE 1=1",
    'list_order_by': "ORDER BY category, subject",
    'list_columns': [
        {'key': 'knowledge_id', 'header': 'ID', 'width': 50, 'anchor': 'center'},
        {'key': 'category',     'header': 'Category', 'width': 120},
        {'key': 'subject',      'header': 'Subject', 'width': 200},
        {'key': 'description',  'header': 'Description', 'width': 380, 'format': _none_dash},
    ],
    'form_fields': [
        {'key': 'subject',     'label': 'Subject', 'type': 'text', 'required': True},
        {'key': 'category',    'label': 'Category', 'type': 'enum',
         'values': KNOWLEDGE_CAT, 'default': 'Frontend'},
        {'key': 'description', 'label': 'Description', 'type': 'textarea'},
    ],
}


PROJECT = {
    'table': 'Project', 'pk': 'project_id', 'singular': 'project',
    'title': 'Projects', 'subtitle': 'Project portfolio',
    'edit_permission': 'project.create',
    'list_sql': """SELECT p.*, c.customer_name FROM Project p
                   LEFT JOIN Customer c ON c.customer_id = p.customer_id
                   WHERE 1=1""",
    'list_order_by': "ORDER BY p.start_date DESC, p.project_code",
    'project_scoped': True,
    'project_filter_clause': 'AND p.project_id IN (__IDS__)',
    'list_columns': [
        {'key': 'project_id',     'header': 'ID', 'width': 50, 'anchor': 'center'},
        {'key': 'project_code',   'header': 'Code', 'width': 90},
        {'key': 'project_name',   'header': 'Name', 'width': 240},
        {'key': 'customer_name',  'header': 'Customer', 'width': 160, 'format': _none_dash},
        {'key': 'status',         'header': 'Status', 'width': 110, 'anchor': 'center'},
        {'key': 'priority',       'header': 'Priority', 'width': 80, 'anchor': 'center'},
        {'key': 'budget',         'header': 'Budget', 'width': 100, 'anchor': 'e', 'format': _money},
        {'key': 'actual_cost',    'header': 'Actual', 'width': 100, 'anchor': 'e', 'format': _money},
        {'key': 'start_date',     'header': 'Start', 'width': 90, 'anchor': 'center', 'format': _none_dash},
        {'key': 'end_date',       'header': 'End', 'width': 90, 'anchor': 'center', 'format': _none_dash},
    ],
    'form_fields': [
        {'key': 'project_name',    'label': 'Name', 'type': 'text', 'required': True},
        {'key': 'project_code',    'label': 'Code (PRJ-XXX)', 'type': 'text'},
        {'key': 'customer_id',     'label': 'Customer', 'type': 'fk',
         'choices_fn': customers_lookup, 'nullable': True},
        {'key': 'description',     'label': 'Description', 'type': 'textarea'},
        {'key': 'status',          'label': 'Status', 'type': 'enum',
         'values': PROJECT_STATUS, 'default': 'planning'},
        {'key': 'priority',        'label': 'Priority', 'type': 'enum',
         'values': PRIORITY, 'default': 'medium'},
        {'key': 'estimated_hours', 'label': 'Estimated hours', 'type': 'real'},
        {'key': 'actual_hours',    'label': 'Actual hours', 'type': 'real'},
        {'key': 'budget',          'label': 'Budget (EUR)', 'type': 'real'},
        {'key': 'actual_cost',     'label': 'Actual cost (EUR)', 'type': 'real'},
        {'key': 'start_date',      'label': 'Start date (YYYY-MM-DD)', 'type': 'date'},
        {'key': 'end_date',        'label': 'End date (YYYY-MM-DD)', 'type': 'date'},
    ],
    'auto_now_fields': ['created_at'],
}


TASK = {
    'table': 'Task', 'pk': 'task_id', 'singular': 'task',
    'title': 'Tasks', 'subtitle': 'Work items across projects',
    'list_sql': """SELECT t.*, p.project_code, p.project_name,
                          COALESCE(e.first_name || ' ' || e.last_name,
                                   x.first_name || ' ' || x.last_name) AS assignee
                   FROM Task t
                   LEFT JOIN Project p ON p.project_id = t.project_id
                   LEFT JOIN Employee e ON e.employee_id = t.assigned_employee_id
                   LEFT JOIN External_Resource x ON x.external_id = t.assigned_external_id
                   WHERE 1=1""",
    'list_order_by': "ORDER BY t.due_date, t.task_id DESC",
    'project_scoped': True,
    'project_filter_clause': 'AND t.project_id IN (__IDS__)',
    'list_columns': [
        {'key': 'task_id',       'header': 'ID', 'width': 50, 'anchor': 'center'},
        {'key': 'project_code',  'header': 'Project', 'width': 90, 'format': _none_dash},
        {'key': 'title',         'header': 'Title', 'width': 280},
        {'key': 'assignee',      'header': 'Assignee', 'width': 160, 'format': _none_dash},
        {'key': 'status',        'header': 'Status', 'width': 100, 'anchor': 'center'},
        {'key': 'priority',      'header': 'Priority', 'width': 80, 'anchor': 'center'},
        {'key': 'due_date',      'header': 'Due', 'width': 90, 'anchor': 'center', 'format': _none_dash},
        {'key': 'estimated_hours','header': 'Est.', 'width': 60, 'anchor': 'e', 'format': _none_dash},
        {'key': 'actual_hours',   'header': 'Actual', 'width': 60, 'anchor': 'e', 'format': _none_dash},
    ],
    'form_fields': [
        {'key': 'project_id',           'label': 'Project', 'type': 'fk',
         'choices_fn': projects_lookup, 'required': True},
        {'key': 'title',                'label': 'Title', 'type': 'text', 'required': True},
        {'key': 'description',          'label': 'Description', 'type': 'textarea'},
        {'key': 'assigned_employee_id', 'label': 'Assignee (employee)', 'type': 'fk',
         'choices_fn': employees_lookup, 'nullable': True},
        {'key': 'assigned_external_id', 'label': 'Assignee (external) — pick only ONE', 'type': 'fk',
         'choices_fn': externals_lookup, 'nullable': True},
        {'key': 'status',         'label': 'Status', 'type': 'enum',
         'values': TASK_STATUS, 'default': 'todo'},
        {'key': 'priority',       'label': 'Priority', 'type': 'enum',
         'values': PRIORITY, 'default': 'medium'},
        {'key': 'estimated_hours','label': 'Estimated hours', 'type': 'real'},
        {'key': 'actual_hours',   'label': 'Actual hours', 'type': 'real'},
        {'key': 'due_date',       'label': 'Due date (YYYY-MM-DD)', 'type': 'date'},
        {'key': 'completed_date', 'label': 'Completed date (YYYY-MM-DD)', 'type': 'date'},
    ],
    'auto_now_fields': ['created_at'],
}


ASSIGNMENT = {
    'table': 'Project_Assignment', 'pk': 'assignment_id', 'singular': 'assignment',
    'title': 'Assignments', 'subtitle': 'Resource allocations to projects',
    'list_sql': """SELECT a.*, p.project_code, p.project_name,
                          COALESCE(e.first_name || ' ' || e.last_name,
                                   x.first_name || ' ' || x.last_name) AS person,
                          CASE WHEN a.employee_id IS NOT NULL THEN 'internal' ELSE 'external' END AS kind
                   FROM Project_Assignment a
                   LEFT JOIN Project p ON p.project_id = a.project_id
                   LEFT JOIN Employee e ON e.employee_id = a.employee_id
                   LEFT JOIN External_Resource x ON x.external_id = a.external_id
                   WHERE 1=1""",
    'list_order_by': "ORDER BY a.start_date DESC",
    'project_scoped': True,
    'project_filter_clause': 'AND a.project_id IN (__IDS__)',
    'list_columns': [
        {'key': 'assignment_id',  'header': 'ID', 'width': 50, 'anchor': 'center'},
        {'key': 'project_code',   'header': 'Project', 'width': 90, 'format': _none_dash},
        {'key': 'person',         'header': 'Person', 'width': 200, 'format': _none_dash},
        {'key': 'kind',           'header': 'Type', 'width': 80, 'anchor': 'center'},
        {'key': 'role_in_project','header': 'Role', 'width': 180, 'format': _none_dash},
        {'key': 'allocated_hours','header': 'Hours', 'width': 70, 'anchor': 'e', 'format': _none_dash},
        {'key': 'start_date',     'header': 'Start', 'width': 90, 'anchor': 'center', 'format': _none_dash},
        {'key': 'end_date',       'header': 'End', 'width': 90, 'anchor': 'center', 'format': _none_dash},
    ],
    'form_fields': [
        {'key': 'project_id',      'label': 'Project', 'type': 'fk',
         'choices_fn': projects_lookup, 'required': True},
        {'key': 'employee_id',     'label': 'Employee (internal) — pick ONE of these two', 'type': 'fk',
         'choices_fn': employees_lookup, 'nullable': True},
        {'key': 'external_id',     'label': 'External resource', 'type': 'fk',
         'choices_fn': externals_lookup, 'nullable': True},
        {'key': 'role_in_project', 'label': 'Role in project', 'type': 'text'},
        {'key': 'allocated_hours', 'label': 'Allocated hours', 'type': 'real'},
        {'key': 'start_date',      'label': 'Start date (YYYY-MM-DD)', 'type': 'date'},
        {'key': 'end_date',        'label': 'End date (YYYY-MM-DD)', 'type': 'date'},
    ],
}


TIME_ENTRY = {
    'table': 'Time_Entry', 'pk': 'time_entry_id', 'singular': 'time entry',
    'title': 'Time entries', 'subtitle': 'Hours logged against tasks',
    'list_sql': """SELECT te.*, t.title AS task_title, p.project_code,
                          COALESCE(e.first_name || ' ' || e.last_name,
                                   x.first_name || ' ' || x.last_name) AS person
                   FROM Time_Entry te
                   LEFT JOIN Task t ON t.task_id = te.task_id
                   LEFT JOIN Project p ON p.project_id = t.project_id
                   LEFT JOIN Employee e ON e.employee_id = te.employee_id
                   LEFT JOIN External_Resource x ON x.external_id = te.external_id
                   WHERE 1=1""",
    'list_order_by': "ORDER BY te.date DESC, te.time_entry_id DESC",
    'project_scoped': True,
    'project_filter_clause': 'AND p.project_id IN (__IDS__)',
    'list_columns': [
        {'key': 'time_entry_id', 'header': 'ID', 'width': 50, 'anchor': 'center'},
        {'key': 'date',          'header': 'Date', 'width': 90, 'anchor': 'center'},
        {'key': 'project_code',  'header': 'Project', 'width': 90, 'format': _none_dash},
        {'key': 'task_title',    'header': 'Task', 'width': 240, 'format': _none_dash},
        {'key': 'person',        'header': 'Person', 'width': 160, 'format': _none_dash},
        {'key': 'hours',         'header': 'Hours', 'width': 70, 'anchor': 'e'},
        {'key': 'billable',      'header': 'Billable', 'width': 80, 'anchor': 'center'},
        {'key': 'description',   'header': 'Description', 'width': 280, 'format': _none_dash},
    ],
    'form_fields': [
        {'key': 'task_id',     'label': 'Task', 'type': 'fk',
         'choices_fn': tasks_lookup, 'required': True},
        {'key': 'employee_id', 'label': 'Employee — pick ONE of these two', 'type': 'fk',
         'choices_fn': employees_lookup, 'nullable': True},
        {'key': 'external_id', 'label': 'External resource', 'type': 'fk',
         'choices_fn': externals_lookup, 'nullable': True},
        {'key': 'date',        'label': 'Date (YYYY-MM-DD)', 'type': 'date', 'required': True},
        {'key': 'hours',       'label': 'Hours', 'type': 'real', 'required': True},
        {'key': 'description', 'label': 'Description', 'type': 'textarea'},
        {'key': 'billable',    'label': 'Billable', 'type': 'enum',
         'values': BILLABLE, 'default': 'yes'},
    ],
}


RISK = {
    'table': 'Project_Risk', 'pk': 'risk_id', 'singular': 'risk',
    'title': 'Risks', 'subtitle': 'Project risk register',
    'list_sql': """SELECT r.*, p.project_code, p.project_name FROM Project_Risk r
                   LEFT JOIN Project p ON p.project_id = r.project_id
                   WHERE 1=1""",
    'list_order_by': "ORDER BY r.identified_date DESC, r.risk_id DESC",
    'project_scoped': True,
    'project_filter_clause': 'AND r.project_id IN (__IDS__)',
    'list_columns': [
        {'key': 'risk_id',         'header': 'ID', 'width': 50, 'anchor': 'center'},
        {'key': 'project_code',    'header': 'Project', 'width': 90, 'format': _none_dash},
        {'key': 'description',     'header': 'Description', 'width': 380},
        {'key': 'probability',     'header': 'Prob.', 'width': 70, 'anchor': 'center'},
        {'key': 'impact',          'header': 'Impact', 'width': 70, 'anchor': 'center'},
        {'key': 'status',          'header': 'Status', 'width': 100, 'anchor': 'center'},
        {'key': 'identified_date', 'header': 'Identified', 'width': 100, 'anchor': 'center', 'format': _none_dash},
    ],
    'form_fields': [
        {'key': 'project_id',      'label': 'Project', 'type': 'fk',
         'choices_fn': projects_lookup, 'required': True},
        {'key': 'description',     'label': 'Description', 'type': 'textarea', 'required': True},
        {'key': 'probability',     'label': 'Probability', 'type': 'enum',
         'values': PROB_IMPACT, 'default': 'medium'},
        {'key': 'impact',          'label': 'Impact', 'type': 'enum',
         'values': PROB_IMPACT, 'default': 'medium'},
        {'key': 'mitigation_plan', 'label': 'Mitigation plan', 'type': 'textarea'},
        {'key': 'status',          'label': 'Status', 'type': 'enum',
         'values': RISK_STATUS, 'default': 'identified'},
        {'key': 'identified_date', 'label': 'Identified date (YYYY-MM-DD)', 'type': 'date'},
    ],
}


INVOICE = {
    'table': 'Invoice', 'pk': 'invoice_id', 'singular': 'invoice',
    'title': 'Invoices', 'subtitle': 'Billing and revenue tracking',
    'edit_permission': 'invoice.manage_all',
    'list_sql': """SELECT i.*, p.project_code, c.customer_name FROM Invoice i
                   LEFT JOIN Project p ON p.project_id = i.project_id
                   LEFT JOIN Customer c ON c.customer_id = i.customer_id
                   WHERE 1=1""",
    'list_order_by': "ORDER BY i.invoice_date DESC",
    'project_scoped': True,
    'project_filter_clause': 'AND i.project_id IN (__IDS__)',
    'list_columns': [
        {'key': 'invoice_id',     'header': 'ID', 'width': 50, 'anchor': 'center'},
        {'key': 'invoice_number', 'header': 'Number', 'width': 130},
        {'key': 'invoice_date',   'header': 'Date', 'width': 90, 'anchor': 'center'},
        {'key': 'customer_name',  'header': 'Customer', 'width': 180, 'format': _none_dash},
        {'key': 'project_code',   'header': 'Project', 'width': 90, 'format': _none_dash},
        {'key': 'total_amount',   'header': 'Amount', 'width': 110, 'anchor': 'e', 'format': _money},
        {'key': 'due_date',       'header': 'Due', 'width': 90, 'anchor': 'center'},
        {'key': 'status',         'header': 'Status', 'width': 100, 'anchor': 'center'},
    ],
    'form_fields': [
        {'key': 'invoice_number', 'label': 'Number (INV-YYYY-XXX)', 'type': 'text'},
        {'key': 'project_id',     'label': 'Project', 'type': 'fk',
         'choices_fn': projects_lookup, 'nullable': True},
        {'key': 'customer_id',    'label': 'Customer', 'type': 'fk',
         'choices_fn': customers_lookup, 'nullable': True},
        {'key': 'invoice_date',   'label': 'Invoice date (YYYY-MM-DD)', 'type': 'date', 'required': True},
        {'key': 'due_date',       'label': 'Due date (YYYY-MM-DD)', 'type': 'date', 'required': True},
        {'key': 'total_amount',   'label': 'Total amount (EUR)', 'type': 'real', 'required': True},
        {'key': 'status',         'label': 'Status', 'type': 'enum',
         'values': INVOICE_STATUS, 'default': 'draft'},
        {'key': 'notes',          'label': 'Notes', 'type': 'textarea'},
    ],
}


# Map of view_id (matches NAV_ITEMS in app.py) -> config
VIEW_CONFIGS = {
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
