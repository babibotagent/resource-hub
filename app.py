"""
ResourceHub v2.1 - Project Management
Tkinter shell with authentication + RBAC.

Boot order:
  1. init_database (creates schema)
  2. ensure_default_admin (creates admin/admin if no users yet)
  3. LoginView (modal) - user signs in
  4. ChangePasswordDialog if must_change_password is set
  5. Main window with sidebar + content area

Logs to data/app.log for troubleshooting visibility/startup issues.
"""

from __future__ import annotations

import logging
import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk

import auth
import database as db
import i18n
from views.dashboard_view import DashboardView
from views.login_view import LoginView, ChangePasswordDialog
from views.users_view import UsersView
from views.crud_view import CrudView
from views.crud_configs import VIEW_CONFIGS


ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
LOGO_SIDEBAR_PATH = os.path.join(ASSETS_DIR, 'logo_64.png')
LOGO_ICON_PATH    = os.path.join(ASSETS_DIR, 'logo_128.png')

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'app.log')


def _setup_logging():
    """File + stderr logger so we can see what happens even on a silent run."""
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(LOG_PATH, mode='a', encoding='utf-8'),
            logging.StreamHandler(sys.stderr),
        ],
    )


COLORS = {
    'primary':       '#2563eb',
    'primary_dark':  '#1e40af',
    'secondary':     '#64748b',
    'success':       '#10b981',
    'warning':       '#f59e0b',
    'danger':        '#ef4444',
    'background':    '#f8fafc',
    'surface':       '#ffffff',
    'text':          '#1e293b',
    'text_light':    '#64748b',
    'border':        '#e2e8f0',
    'sidebar':       '#1e293b',
    'sidebar_hover': '#334155',
}


# (view_id, i18n_key, allowed_roles)
NAV_ITEMS = [
    ('dashboard',   'nav.dashboard',   'all'),
    ('projects',    'nav.projects',    'all'),
    ('tasks',       'nav.tasks',       'all'),
    ('assignments', 'nav.assignments', 'all'),
    ('timeentries', 'nav.timeentries', 'all'),
    ('risks',       'nav.risks',       'all'),
    ('invoices',    'nav.invoices',    ('admin', 'project_manager')),
    ('employees',   'nav.employees',   ('admin',)),
    ('externals',   'nav.externals',   ('admin',)),
    ('customers',   'nav.customers',   ('admin',)),
    ('knowledge',   'nav.knowledge',   ('admin',)),
    ('departments', 'nav.departments', ('admin',)),
    ('reports',     'nav.reports',     ('admin', 'project_manager')),
    ('users',       'nav.users',       ('admin',)),
]


def _can_see(view_id):
    """Whether the current user is allowed to see this nav item."""
    user = auth.current_user()
    if user is None:
        return False
    if user['role'] == 'admin':
        return True
    for vid, _, allowed in NAV_ITEMS:
        if vid == view_id:
            return allowed == 'all' or user['role'] in allowed
    return False


def _clear_root(root):
    """Remove every child widget from root — used when switching from
    login state to main-app state without destroying the Tk root itself."""
    for child in list(root.winfo_children()):
        try:
            child.destroy()
        except Exception:
            pass


class ResourceManagerApp:
    """Top-level application window. Built only after a successful login.

    Re-uses the existing Tk root passed in (we don't create a new one),
    so the login window and the main window share the same taskbar entry.
    """

    def __init__(self, root):
        self.root = root
        self.colors = COLORS
        self._logo_sidebar = None
        self._logo_icon = None
        self._nav_buttons = {}
        self._current_view = 'dashboard'

        _clear_root(self.root)

        self._configure_window()
        self._setup_styles()
        self._build_layout()

        self.show_view('dashboard')

        i18n.add_listener(self._on_language_change)
        auth.add_listener(self._on_user_change)

    # ------------------------------------------------------------------ window
    def _configure_window(self):
        self.root.title(i18n.t('app.title'))
        self.root.geometry('1400x820')
        self.root.minsize(1200, 700)
        self.root.configure(bg=self.colors['background'])
        try:
            self._logo_icon = tk.PhotoImage(file=LOGO_ICON_PATH)
            self.root.iconphoto(True, self._logo_icon)
        except Exception:
            pass

    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass
        style.configure('Treeview',
                        background='white', fieldbackground='white',
                        foreground=self.colors['text'], rowheight=28,
                        borderwidth=0, font=('Segoe UI', 9))
        style.configure('Treeview.Heading',
                        background=self.colors['background'],
                        foreground=self.colors['text'], relief='flat',
                        font=('Segoe UI', 9, 'bold'), padding=(10, 6))
        style.map('Treeview',
                  background=[('selected', self.colors['primary'])],
                  foreground=[('selected', 'white')])

    # ------------------------------------------------------------------ layout
    def _build_layout(self):
        main = tk.Frame(self.root, bg=self.colors['background'])
        main.pack(fill='both', expand=True)

        # Sidebar
        self.sidebar = tk.Frame(main, bg=self.colors['sidebar'], width=240)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        # Logo
        logo_frame = tk.Frame(self.sidebar, bg=self.colors['sidebar'])
        logo_frame.pack(fill='x', pady=(20, 6))
        try:
            self._logo_sidebar = tk.PhotoImage(file=LOGO_SIDEBAR_PATH)
            tk.Label(logo_frame, image=self._logo_sidebar,
                     bg=self.colors['sidebar']).pack()
        except Exception:
            tk.Label(logo_frame, text='[RH]', font=('Segoe UI', 22, 'bold'),
                     bg=self.colors['sidebar'], fg='white').pack()
        self._title_label = tk.Label(logo_frame, text='ResourceHub',
                                     font=('Segoe UI', 13, 'bold'),
                                     bg=self.colors['sidebar'], fg='white')
        self._title_label.pack(pady=(6, 0))
        self._tagline_label = tk.Label(logo_frame, text=i18n.t('app.tagline'),
                                       font=('Segoe UI', 9),
                                       bg=self.colors['sidebar'],
                                       fg=self.colors['text_light'])
        self._tagline_label.pack()

        tk.Frame(self.sidebar, bg=self.colors['sidebar_hover'], height=1
                 ).pack(fill='x', padx=20, pady=10)

        # Nav container
        self._nav_container = tk.Frame(self.sidebar, bg=self.colors['sidebar'])
        self._nav_container.pack(fill='both', expand=True)
        self._build_nav()

        # Footer
        footer = tk.Frame(self.sidebar, bg=self.colors['sidebar'])
        footer.pack(side='bottom', fill='x', pady=12)

        self._user_card = tk.Frame(footer, bg=self.colors['sidebar_hover'])
        self._user_card.pack(fill='x', padx=12, pady=(0, 10))
        self._user_label = tk.Label(self._user_card, text='', anchor='w',
                                    font=('Segoe UI', 10, 'bold'),
                                    bg=self.colors['sidebar_hover'],
                                    fg='white', padx=10, pady=6)
        self._user_label.pack(fill='x')
        self._role_label = tk.Label(self._user_card, text='', anchor='w',
                                    font=('Segoe UI', 9),
                                    bg=self.colors['sidebar_hover'],
                                    fg=self.colors['text_light'],
                                    padx=10)
        self._role_label.pack(fill='x', pady=(0, 4))
        self._logout_btn = tk.Button(self._user_card,
                                     text=i18n.t('btn.logout'),
                                     font=('Segoe UI', 9),
                                     bg=self.colors['sidebar'], fg='white',
                                     bd=0, padx=10, pady=4, cursor='hand2',
                                     command=self._on_logout)
        self._logout_btn.pack(fill='x', padx=8, pady=(0, 8))

        lang_box = tk.Frame(footer, bg=self.colors['sidebar'])
        lang_box.pack(pady=(0, 6))
        self._lang_label = tk.Label(lang_box, text=i18n.t('app.language') + ':',
                                    font=('Segoe UI', 9),
                                    bg=self.colors['sidebar'],
                                    fg=self.colors['text_light'])
        self._lang_label.pack(side='left', padx=(0, 6))
        self._lang_buttons = {}
        for code in ('en', 'fr'):
            b = tk.Button(lang_box, text=code.upper(),
                          font=('Segoe UI', 9, 'bold'),
                          bd=0, padx=8, pady=2, cursor='hand2',
                          command=lambda c=code: i18n.set_language(c))
            b.pack(side='left', padx=2)
            self._lang_buttons[code] = b
        self._refresh_lang_buttons()

        tk.Label(footer, text=i18n.t('app.version'), font=('Segoe UI', 8),
                 bg=self.colors['sidebar'],
                 fg=self.colors['text_light']).pack()

        self._refresh_user_card()

        self.content_frame = tk.Frame(main, bg=self.colors['background'])
        self.content_frame.pack(side='left', fill='both', expand=True)

    def _build_nav(self):
        for child in self._nav_container.winfo_children():
            child.destroy()
        self._nav_buttons = {}
        for view_id, label_key, _allowed in NAV_ITEMS:
            if not _can_see(view_id):
                continue
            btn = tk.Button(self._nav_container, text=i18n.t(label_key),
                            font=('Segoe UI', 10),
                            bg=self.colors['sidebar'], fg='white',
                            activebackground=self.colors['sidebar_hover'],
                            activeforeground='white',
                            bd=0, anchor='w', padx=22, pady=10, cursor='hand2',
                            command=lambda v=view_id: self.show_view(v))
            btn.pack(fill='x', padx=10, pady=2)
            self._nav_buttons[view_id] = btn
        if self._current_view not in self._nav_buttons:
            self._current_view = 'dashboard'

    def _refresh_user_card(self):
        u = auth.current_user()
        if not u:
            self._user_label.configure(text='')
            self._role_label.configure(text='')
            return
        self._user_label.configure(text=u['username'])
        self._role_label.configure(text=i18n.t(f"role.{u['role']}"))
        self._logout_btn.configure(text=i18n.t('btn.logout'))

    def show_view(self, view_name):
        if not _can_see(view_name):
            view_name = 'dashboard'
        self._current_view = view_name
        for w in self.content_frame.winfo_children():
            w.destroy()
        for view_id, btn in self._nav_buttons.items():
            if view_id == view_name:
                btn.configure(bg=self.colors['primary'],
                              font=('Segoe UI', 10, 'bold'))
            else:
                btn.configure(bg=self.colors['sidebar'],
                              font=('Segoe UI', 10))
        if view_name == 'dashboard':
            DashboardView(self.content_frame, self.colors)
        elif view_name == 'users':
            UsersView(self.content_frame, self.colors)
        elif view_name in VIEW_CONFIGS:
            CrudView(self.content_frame, self.colors, VIEW_CONFIGS[view_name])
        elif view_name == 'reports':
            self._render_reports()
        else:
            self._render_coming_soon(view_name)

    def _render_reports(self):
        """Quick aggregated reports — hours per project, billable revenue,
        top performers — read straight from the DB."""
        from database import get_connection
        wrap = tk.Frame(self.content_frame, bg=self.colors['background'])
        wrap.pack(fill='both', expand=True, padx=24, pady=20)
        tk.Label(wrap, text='Reports', font=('Segoe UI', 22, 'bold'),
                 bg=self.colors['background'], fg=self.colors['text']
                 ).pack(anchor='w')
        tk.Label(wrap, text='Aggregated views across the portfolio',
                 font=('Segoe UI', 11),
                 bg=self.colors['background'], fg=self.colors['text_light']
                 ).pack(anchor='w', pady=(2, 12))

        notebook = ttk.Notebook(wrap)
        notebook.pack(fill='both', expand=True)

        def _make_tab(title, sql, headers, cols, formatters=None):
            tab = tk.Frame(notebook, bg=self.colors['surface'])
            notebook.add(tab, text=title)
            tree = ttk.Treeview(tab, columns=cols, show='headings')
            for c, h in zip(cols, headers):
                tree.heading(c, text=h)
                tree.column(c, anchor='w', width=160, stretch=True)
            tree.pack(fill='both', expand=True, padx=4, pady=4)
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute(sql)
                rows = cur.fetchall()
            for row in rows:
                values = []
                for c in cols:
                    v = row[c]
                    fmt = (formatters or {}).get(c)
                    if fmt:
                        values.append(fmt(v))
                    elif v is None:
                        values.append('-')
                    else:
                        values.append(v)
                tree.insert('', 'end', values=values)

        money = lambda v: f"{float(v):,.2f}" if v not in (None, '') else '-'

        _make_tab('Hours by project', """
            SELECT p.project_code, p.project_name, p.status,
                   COALESCE(SUM(te.hours), 0) AS total_hours,
                   COALESCE(SUM(CASE WHEN te.billable='yes' THEN te.hours ELSE 0 END), 0) AS billable_hours
              FROM Project p
              LEFT JOIN Task t ON t.project_id = p.project_id
              LEFT JOIN Time_Entry te ON te.task_id = t.task_id
             GROUP BY p.project_id
             ORDER BY total_hours DESC
        """, ['Code', 'Project', 'Status', 'Total hours', 'Billable hours'],
             ['project_code', 'project_name', 'status', 'total_hours', 'billable_hours'])

        _make_tab('Budget vs actual', """
            SELECT project_code, project_name, status,
                   COALESCE(budget,0) AS budget,
                   COALESCE(actual_cost,0) AS actual_cost,
                   CASE WHEN budget IS NULL OR budget = 0 THEN 0
                        ELSE ROUND(100.0 * COALESCE(actual_cost,0) / budget, 1)
                   END AS pct_spent
              FROM Project
             ORDER BY pct_spent DESC
        """, ['Code', 'Project', 'Status', 'Budget', 'Actual', '% spent'],
             ['project_code', 'project_name', 'status', 'budget', 'actual_cost', 'pct_spent'],
             {'budget': money, 'actual_cost': money})

        _make_tab('Hours by person', """
            SELECT person, COALESCE(SUM(hours),0) AS total_hours,
                   COALESCE(SUM(CASE WHEN billable='yes' THEN hours ELSE 0 END), 0) AS billable_hours
              FROM (
                  SELECT (e.first_name || ' ' || e.last_name) AS person, te.hours, te.billable
                    FROM Time_Entry te JOIN Employee e ON e.employee_id = te.employee_id
                  UNION ALL
                  SELECT (x.first_name || ' ' || x.last_name) AS person, te.hours, te.billable
                    FROM Time_Entry te JOIN External_Resource x ON x.external_id = te.external_id
              )
             GROUP BY person
             ORDER BY total_hours DESC
        """, ['Person', 'Total hours', 'Billable hours'],
             ['person', 'total_hours', 'billable_hours'])

        _make_tab('Invoices by status', """
            SELECT status, COUNT(*) AS n, COALESCE(SUM(total_amount),0) AS amount
              FROM Invoice GROUP BY status ORDER BY status
        """, ['Status', 'Count', 'Total amount'],
             ['status', 'n', 'amount'],
             {'amount': money})

    def _render_coming_soon(self, view_name):
        wrap = tk.Frame(self.content_frame, bg=self.colors['background'])
        wrap.pack(fill='both', expand=True, padx=40, pady=60)
        label_key = next((k for v, k, _ in NAV_ITEMS if v == view_name),
                         'common.coming_soon')
        tk.Label(wrap, text=i18n.t(label_key),
                 font=('Segoe UI', 22, 'bold'),
                 bg=self.colors['background'],
                 fg=self.colors['text']).pack(anchor='w')
        tk.Label(wrap, text=i18n.t('common.coming_soon'),
                 font=('Segoe UI', 13, 'bold'),
                 bg=self.colors['background'],
                 fg=self.colors['warning']).pack(anchor='w', pady=(20, 6))
        tk.Label(wrap, text=i18n.t('common.coming_soon.desc'),
                 font=('Segoe UI', 11), wraplength=720, justify='left',
                 bg=self.colors['background'],
                 fg=self.colors['text_light']).pack(anchor='w')

    def _refresh_lang_buttons(self):
        active = i18n.get_language()
        for code, btn in self._lang_buttons.items():
            if code == active:
                btn.configure(bg=self.colors['primary'], fg='white')
            else:
                btn.configure(bg=self.colors['sidebar_hover'],
                              fg=self.colors['text_light'])

    def _on_language_change(self, _new_lang):
        self.root.title(i18n.t('app.title'))
        self._tagline_label.configure(text=i18n.t('app.tagline'))
        self._lang_label.configure(text=i18n.t('app.language') + ':')
        self._refresh_lang_buttons()
        self._build_nav()
        self._refresh_user_card()
        self.show_view(self._current_view)

    def _on_user_change(self, new_user):
        self._build_nav()
        self._refresh_user_card()
        if new_user is None:
            return
        self.show_view(self._current_view)

    def _on_logout(self):
        if not messagebox.askyesno(i18n.t('common.confirm'),
                                   i18n.t('btn.logout') + '?'):
            return
        logging.info("User logging out")
        auth.logout()
        # Tear down main UI and re-show the login on the SAME root window.
        _clear_root(self.root)
        self.root.geometry('480x560')
        user = LoginView.run(self.root, COLORS)
        if user is None:
            self.root.destroy()
            return
        if user.get('must_change_password'):
            ok = ChangePasswordDialog.run(self.root, COLORS, user, force=True)
            if not ok:
                self.root.destroy()
                return
        # Rebuild the main UI on the same root
        ResourceManagerApp(self.root)


def _check_first_run():
    counts = db.table_counts()
    if counts.get('Project', 0) > 0:
        return
    ans = messagebox.askyesno(
        i18n.t('firstrun.title'),
        i18n.t('firstrun.message'),
    )
    if ans:
        try:
            from import_excel import import_workbook
            import_workbook(do_reset=True)
            messagebox.showinfo(i18n.t('common.info'), i18n.t('firstrun.loaded'))
        except Exception as exc:
            messagebox.showerror(i18n.t('common.error'), str(exc))


def main():
    _setup_logging()
    logging.info("=" * 60)
    logging.info("ResourceHub starting")
    logging.info(f"Python: {sys.version}")
    logging.info(f"DB:     {db.DB_PATH}")

    try:
        db.init_database()
        logging.info("Schema initialized")
        created = auth.ensure_default_admin()
        if created:
            logging.info("Default admin/admin created")

        # Use a single Tk root for both login and main app.
        # Showing the root (not withdrawing) ensures the login window is
        # visible and gets a taskbar entry on Windows.
        root = tk.Tk()
        root.title(i18n.t('app.title'))
        root.geometry('480x560')
        root.configure(bg=COLORS['background'])
        try:
            icon = tk.PhotoImage(file=LOGO_ICON_PATH)
            root.iconphoto(True, icon)
            root._login_icon = icon  # keep reference
        except Exception:
            pass
        # Centre on screen
        root.update_idletasks()
        sw = root.winfo_screenwidth(); sh = root.winfo_screenheight()
        x = (sw - 480) // 2; y = (sh - 560) // 2
        root.geometry(f"480x560+{x}+{y}")
        root.lift()
        root.focus_force()
        root.attributes('-topmost', True)
        root.after(200, lambda: root.attributes('-topmost', False))

        logging.info("Tk root created and centred")

        _check_first_run()
        logging.info("First-run check complete")

        user = LoginView.run(root, COLORS)
        if user is None:
            logging.info("User cancelled login; exiting")
            try: root.destroy()
            except Exception: pass
            sys.exit(0)
        logging.info(f"Login OK as {user['username']!r} (role={user['role']!r}, "
                     f"must_change={user['must_change_password']})")

        if user.get('must_change_password'):
            logging.info("Forcing password change")
            ok = ChangePasswordDialog.run(root, COLORS, user, force=True)
            if not ok:
                logging.info("User cancelled forced password change; exiting")
                root.destroy()
                sys.exit(0)
            logging.info("Password changed")

        # Build the main app on the same root window
        ResourceManagerApp(root)
        logging.info("Main window built; entering mainloop")
        root.mainloop()
        logging.info("Mainloop exited cleanly")
    except SystemExit:
        raise
    except Exception:
        logging.exception("Unhandled exception during startup")
        try:
            messagebox.showerror("ResourceHub - Fatal error",
                                 "An error occurred. See data/app.log for details.")
        except Exception:
            pass
        raise


if __name__ == '__main__':
    main()
