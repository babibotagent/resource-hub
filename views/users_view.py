"""
Users management view (admin only).

Top half: list of users with New / Edit / Delete / Reset password actions.
Bottom half: project-access grants for the selected user, with Add / Remove.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import auth
import i18n
from database import get_connection


ROLE_VALUES = ('admin', 'project_manager', 'member', 'viewer')
PROJECT_ROLE_VALUES = ('project_manager', 'member', 'viewer')


def _employees_for_combobox():
    """Return list of (label, employee_id_or_None) for the link picker."""
    out = [('-', None)]
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT employee_id, first_name, last_name, email
                         FROM Employee ORDER BY first_name, last_name""")
        for r in cur.fetchall():
            out.append((f"{r['first_name']} {r['last_name']} <{r['email'] or ''}>",
                        r['employee_id']))
    return out


def _projects_for_combobox():
    out = []
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT project_id, project_code, project_name FROM Project "
                    "ORDER BY project_code")
        for r in cur.fetchall():
            out.append((f"{r['project_code']} - {r['project_name']}", r['project_id']))
    return out


class UsersView(tk.Frame):
    """Administrative view: manage users + per-project access."""

    def __init__(self, parent, colors):
        super().__init__(parent, bg=colors['background'])
        self.colors = colors
        self.pack(fill='both', expand=True)
        self._selected_user_id = None

        if not auth.is_admin():
            self._render_denied()
            return

        i18n.add_listener(self._on_language_change)
        self.bind('<Destroy>', lambda e: i18n.remove_listener(self._on_language_change))
        self._render()

    # ---------------------------------------------------------------- denied
    def _render_denied(self):
        wrap = tk.Frame(self, bg=self.colors['background'])
        wrap.pack(fill='both', expand=True, padx=40, pady=60)
        tk.Label(wrap, text=i18n.t('common.error'),
                 font=('Segoe UI', 18, 'bold'),
                 bg=self.colors['background'],
                 fg=self.colors['danger']).pack(anchor='w')
        tk.Label(wrap, text=i18n.t('perm.denied'), font=('Segoe UI', 11),
                 bg=self.colors['background'],
                 fg=self.colors['text']).pack(anchor='w', pady=(10, 0))

    # ---------------------------------------------------------------- main
    def _render(self):
        for child in self.winfo_children():
            child.destroy()

        # Header
        header = tk.Frame(self, bg=self.colors['background'])
        header.pack(fill='x', padx=24, pady=(20, 6))
        tk.Label(header, text=i18n.t('users.title'),
                 font=('Segoe UI', 22, 'bold'),
                 bg=self.colors['background'],
                 fg=self.colors['text']).pack(anchor='w')
        tk.Label(header, text=i18n.t('users.subtitle'),
                 font=('Segoe UI', 11),
                 bg=self.colors['background'],
                 fg=self.colors['text_light']).pack(anchor='w', pady=(2, 0))

        # Action buttons
        bar = tk.Frame(self, bg=self.colors['background'])
        bar.pack(fill='x', padx=24, pady=(8, 4))
        self._btn(bar, i18n.t('btn.new'), self._on_new, primary=True
                  ).pack(side='left', padx=(0, 6))
        self._btn(bar, i18n.t('btn.edit'), self._on_edit
                  ).pack(side='left', padx=6)
        self._btn(bar, i18n.t('btn.reset_password'), self._on_reset_pwd
                  ).pack(side='left', padx=6)
        self._btn(bar, i18n.t('btn.delete'), self._on_delete, danger=True
                  ).pack(side='left', padx=6)
        self._btn(bar, i18n.t('btn.refresh'), self._refresh
                  ).pack(side='right')

        # Users table
        tbl_frame = tk.Frame(self, bg=self.colors['surface'],
                             highlightbackground=self.colors['border'],
                             highlightthickness=1)
        tbl_frame.pack(fill='both', expand=True, padx=24, pady=8)

        cols = ('id', 'username', 'role', 'employee', 'active', 'last_login')
        headers = [
            'ID',
            i18n.t('users.col.username'),
            i18n.t('users.col.role'),
            i18n.t('users.col.employee'),
            i18n.t('users.col.active'),
            i18n.t('users.col.last_login'),
        ]
        self.tree = ttk.Treeview(tbl_frame, columns=cols, show='headings')
        for c, h in zip(cols, headers):
            self.tree.heading(c, text=h)
            self.tree.column(c, anchor='w',
                             width=60 if c == 'id' else 160, stretch=True)
        self.tree.column('active', width=80, anchor='center')
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<<TreeviewSelect>>', self._on_select)

        # Project access section (filled when a user is selected)
        access_label = tk.Label(self, text=i18n.t('users.access.title'),
                                font=('Segoe UI', 13, 'bold'),
                                bg=self.colors['background'],
                                fg=self.colors['text'])
        access_label.pack(anchor='w', padx=24, pady=(16, 4))

        access_bar = tk.Frame(self, bg=self.colors['background'])
        access_bar.pack(fill='x', padx=24, pady=(0, 4))
        self._btn(access_bar, i18n.t('users.access.add'), self._on_grant,
                  primary=True).pack(side='left', padx=(0, 6))
        self._btn(access_bar, i18n.t('btn.remove'), self._on_revoke,
                  danger=True).pack(side='left', padx=6)

        access_frame = tk.Frame(self, bg=self.colors['surface'],
                                highlightbackground=self.colors['border'],
                                highlightthickness=1)
        access_frame.pack(fill='x', padx=24, pady=(0, 16))

        ac_cols = ('proj_id', 'project', 'role', 'granted')
        ac_headers = [
            'ID',
            i18n.t('users.access.col.project'),
            i18n.t('users.access.col.role'),
            i18n.t('users.access.col.granted'),
        ]
        self.access_tree = ttk.Treeview(access_frame, columns=ac_cols,
                                        show='headings', height=6)
        for c, h in zip(ac_cols, ac_headers):
            self.access_tree.heading(c, text=h)
            self.access_tree.column(c, anchor='w',
                                    width=60 if c == 'proj_id' else 200,
                                    stretch=True)
        self.access_tree.pack(fill='x')

        self._refresh()

    # ---------------------------------------------------------------- helpers
    def _btn(self, parent, text, cmd, primary=False, danger=False):
        if primary:
            bg, fg = self.colors['primary'], 'white'
        elif danger:
            bg, fg = self.colors['danger'], 'white'
        else:
            bg, fg = self.colors['border'], self.colors['text']
        return tk.Button(parent, text=text, font=('Segoe UI', 9, 'bold'),
                         bg=bg, fg=fg, bd=0, padx=14, pady=6, cursor='hand2',
                         command=cmd)

    def _refresh(self):
        # Users list
        for row in self.tree.get_children():
            self.tree.delete(row)
        for u in auth.list_users():
            self.tree.insert('', 'end', values=(
                u['user_id'], u['username'],
                i18n.t(f"role.{u['role']}"),
                u['employee_name'] or '-',
                i18n.t('common.yes') if u['is_active'] else i18n.t('common.no'),
                u['last_login_at'] or '-',
            ))
        self._refresh_access_table()

    def _refresh_access_table(self):
        for row in self.access_tree.get_children():
            self.access_tree.delete(row)
        if self._selected_user_id is None:
            return
        grants = auth.list_project_access(self._selected_user_id)
        for g in grants:
            self.access_tree.insert('', 'end', values=(
                g['project_id'],
                f"{g['project_code']} - {g['project_name']}",
                i18n.t(f"role.{g['project_role']}"),
                g['granted_at'],
            ))

    # ---------------------------------------------------------------- events
    def _on_select(self, _ev):
        sel = self.tree.selection()
        if not sel:
            self._selected_user_id = None
        else:
            self._selected_user_id = int(self.tree.item(sel[0])['values'][0])
        self._refresh_access_table()

    def _selected_user(self):
        if self._selected_user_id is None:
            return None
        for u in auth.list_users():
            if u['user_id'] == self._selected_user_id:
                return u
        return None

    def _on_new(self):
        UserDialog.run(self.winfo_toplevel(), self.colors,
                       on_save=lambda data: auth.create_user(
                           data['username'], data['password'], data['role'],
                           employee_id=data.get('employee_id'),
                           must_change=data.get('must_change', False),
                       ))
        self._refresh()

    def _on_edit(self):
        u = self._selected_user()
        if not u:
            return
        UserDialog.run(self.winfo_toplevel(), self.colors,
                       existing=u,
                       on_save=lambda data: self._save_edit(u['user_id'], data))
        self._refresh()

    def _save_edit(self, user_id, data):
        auth.update_user(user_id,
                         username=data['username'],
                         role=data['role'],
                         employee_id=data.get('employee_id'),
                         is_active=data['is_active'])
        if data.get('password'):
            auth.set_password(user_id, data['password'],
                              clear_must_change=not data.get('must_change', False))

    def _on_reset_pwd(self):
        u = self._selected_user()
        if not u:
            return
        # Set a random temp password and force change at next login
        import secrets
        tmp = secrets.token_urlsafe(8)
        auth.set_password(u['user_id'], tmp, clear_must_change=False)
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE User SET must_change_password = 1 WHERE user_id = ?",
                        (u['user_id'],))
        messagebox.showinfo(i18n.t('common.info'),
                            f"{u['username']}\n\nTemp password: {tmp}\n\n"
                            f"User must change at next login.")

    def _on_delete(self):
        u = self._selected_user()
        if not u:
            return
        if u['username'] == auth.current_user()['username']:
            messagebox.showerror(i18n.t('common.error'),
                                 "Cannot delete your own account.")
            return
        if not messagebox.askyesno(i18n.t('common.confirm'),
                                   i18n.t('users.confirm.delete')):
            return
        auth.delete_user(u['user_id'])
        self._selected_user_id = None
        self._refresh()

    def _on_grant(self):
        if self._selected_user_id is None:
            return
        ProjectAccessDialog.run(self.winfo_toplevel(), self.colors,
                                user_id=self._selected_user_id)
        self._refresh_access_table()

    def _on_revoke(self):
        if self._selected_user_id is None:
            return
        sel = self.access_tree.selection()
        if not sel:
            return
        project_id = int(self.access_tree.item(sel[0])['values'][0])
        if not messagebox.askyesno(i18n.t('common.confirm'),
                                   i18n.t('common.confirm_delete')):
            return
        auth.revoke_project_access(self._selected_user_id, project_id)
        self._refresh_access_table()

    def _on_language_change(self, _new_lang):
        self._render()


# ===========================================================================
# User create/edit dialog
# ===========================================================================
class UserDialog:
    @classmethod
    def run(cls, root, colors, *, existing=None, on_save=None):
        d = cls(root, colors, existing, on_save)
        root.wait_window(d.window)
        return d.saved

    def __init__(self, root, colors, existing, on_save):
        self.root = root
        self.colors = colors
        self.existing = existing
        self.on_save = on_save
        self.saved = False

        self.window = tk.Toplevel(root)
        self.window.configure(bg=colors['surface'])
        title_key = 'users.dialog.edit' if existing else 'users.dialog.new'
        self.window.title(i18n.t(title_key))
        self.window.geometry('460x520')
        self.window.resizable(False, False)
        self.window.transient(root)
        self.window.grab_set()

        body = tk.Frame(self.window, bg=colors['surface'])
        body.pack(fill='both', expand=True, padx=24, pady=20)

        tk.Label(body, text=i18n.t(title_key),
                 font=('Segoe UI', 14, 'bold'),
                 bg=colors['surface'], fg=colors['text']
                 ).pack(anchor='w', pady=(0, 16))

        # Username
        self._add_label(body, i18n.t('users.field.username'))
        self.username_var = tk.StringVar(value=existing['username'] if existing else '')
        tk.Entry(body, textvariable=self.username_var, font=('Segoe UI', 11),
                 bd=1, relief='solid'
                 ).pack(fill='x', ipady=5, pady=(2, 8))

        # Password
        pwd_label = (i18n.t('users.field.password') + ' '
                     + ('(' + i18n.t('btn.cancel').lower() + '/' + i18n.t('common.empty').lower() + ')'
                        if existing else ''))
        self._add_label(body, i18n.t('users.field.password') +
                        (' (leave blank to keep)' if existing else ''))
        self.password_var = tk.StringVar()
        tk.Entry(body, textvariable=self.password_var, font=('Segoe UI', 11),
                 bd=1, relief='solid', show='*'
                 ).pack(fill='x', ipady=5, pady=(2, 8))

        # Role
        self._add_label(body, i18n.t('users.field.role'))
        self.role_var = tk.StringVar(value=existing['role'] if existing else 'member')
        role_display = [(i18n.t(f"role.{r}"), r) for r in ROLE_VALUES]
        cb = ttk.Combobox(body, state='readonly',
                          values=[d[0] for d in role_display])
        cb.pack(fill='x', pady=(2, 8))
        # Pre-select current role
        for i, (_, code) in enumerate(role_display):
            if code == self.role_var.get():
                cb.current(i)
                break
        self._role_combo = cb
        self._role_display = role_display

        # Employee link
        self._add_label(body, i18n.t('users.field.employee'))
        self._employee_choices = _employees_for_combobox()
        emp_cb = ttk.Combobox(body, state='readonly',
                              values=[d[0] for d in self._employee_choices])
        emp_cb.pack(fill='x', pady=(2, 8))
        if existing and existing.get('employee_id'):
            for i, (_, eid) in enumerate(self._employee_choices):
                if eid == existing['employee_id']:
                    emp_cb.current(i)
                    break
        else:
            emp_cb.current(0)
        self._employee_combo = emp_cb

        # Active checkbox
        self.active_var = tk.IntVar(value=existing['is_active'] if existing else 1)
        tk.Checkbutton(body, text=i18n.t('users.field.active'),
                       variable=self.active_var, bg=colors['surface']
                       ).pack(anchor='w', pady=(6, 4))

        # Must change pw
        self.must_change_var = tk.IntVar(
            value=existing['must_change_password'] if existing else 1)
        tk.Checkbutton(body, text=i18n.t('users.field.must_change'),
                       variable=self.must_change_var, bg=colors['surface']
                       ).pack(anchor='w')

        # Error
        self.error_label = tk.Label(body, text='', font=('Segoe UI', 9),
                                    bg=colors['surface'], fg=colors['danger'],
                                    wraplength=400, justify='left')
        self.error_label.pack(anchor='w', pady=(10, 0))

        # Buttons
        btns = tk.Frame(body, bg=colors['surface'])
        btns.pack(fill='x', pady=(16, 0))
        tk.Button(btns, text=i18n.t('btn.save'),
                  font=('Segoe UI', 10, 'bold'),
                  bg=colors['primary'], fg='white', bd=0, padx=14, pady=8,
                  cursor='hand2', command=self._save
                  ).pack(side='right', padx=(8, 0))
        tk.Button(btns, text=i18n.t('btn.cancel'),
                  font=('Segoe UI', 10),
                  bg=colors['border'], bd=0, padx=14, pady=8, cursor='hand2',
                  command=self.window.destroy
                  ).pack(side='right')

    def _add_label(self, parent, text):
        tk.Label(parent, text=text, font=('Segoe UI', 9),
                 bg=self.colors['surface'], fg=self.colors['text_light']
                 ).pack(anchor='w', pady=(4, 0))

    def _save(self):
        try:
            username = self.username_var.get().strip()
            if not username:
                raise ValueError("Username required.")
            role_idx = self._role_combo.current()
            if role_idx < 0:
                raise ValueError("Pick a role.")
            role = self._role_display[role_idx][1]
            emp_idx = self._employee_combo.current()
            employee_id = self._employee_choices[emp_idx][1] if emp_idx >= 0 else None
            password = self.password_var.get()

            data = {
                'username': username,
                'role': role,
                'employee_id': employee_id,
                'is_active': bool(self.active_var.get()),
                'must_change': bool(self.must_change_var.get()),
            }
            if not self.existing:
                if not password or len(password) < 4:
                    raise ValueError(i18n.t('pwd.change.error.short'))
                data['password'] = password
            else:
                if password:
                    if len(password) < 4:
                        raise ValueError(i18n.t('pwd.change.error.short'))
                    data['password'] = password
            self.on_save(data)
            self.saved = True
            self.window.destroy()
        except Exception as e:
            self.error_label.configure(text=str(e))


# ===========================================================================
# Project access grant dialog
# ===========================================================================
class ProjectAccessDialog:
    @classmethod
    def run(cls, root, colors, *, user_id):
        d = cls(root, colors, user_id)
        root.wait_window(d.window)
        return d.saved

    def __init__(self, root, colors, user_id):
        self.user_id = user_id
        self.saved = False

        self.window = tk.Toplevel(root)
        self.window.configure(bg=colors['surface'])
        self.window.title(i18n.t('users.access.add'))
        self.window.geometry('420x260')
        self.window.resizable(False, False)
        self.window.transient(root)
        self.window.grab_set()

        body = tk.Frame(self.window, bg=colors['surface'])
        body.pack(fill='both', expand=True, padx=24, pady=20)

        tk.Label(body, text=i18n.t('users.access.add'),
                 font=('Segoe UI', 14, 'bold'),
                 bg=colors['surface'], fg=colors['text']
                 ).pack(anchor='w', pady=(0, 16))

        # Project
        tk.Label(body, text=i18n.t('users.access.col.project'),
                 font=('Segoe UI', 9), bg=colors['surface'],
                 fg=colors['text_light']).pack(anchor='w', pady=(4, 0))
        self._project_choices = _projects_for_combobox()
        self.project_combo = ttk.Combobox(body, state='readonly',
            values=[d[0] for d in self._project_choices])
        self.project_combo.pack(fill='x', pady=(2, 8))
        if self._project_choices:
            self.project_combo.current(0)

        # Project role
        tk.Label(body, text=i18n.t('users.access.col.role'),
                 font=('Segoe UI', 9), bg=colors['surface'],
                 fg=colors['text_light']).pack(anchor='w', pady=(4, 0))
        self._role_choices = [(i18n.t(f"role.{r}"), r) for r in PROJECT_ROLE_VALUES]
        self.role_combo = ttk.Combobox(body, state='readonly',
            values=[d[0] for d in self._role_choices])
        self.role_combo.pack(fill='x', pady=(2, 12))
        self.role_combo.current(1)  # member

        self.error_label = tk.Label(body, text='', font=('Segoe UI', 9),
                                    bg=colors['surface'], fg=colors['danger'])
        self.error_label.pack(anchor='w')

        # Buttons
        btns = tk.Frame(body, bg=colors['surface'])
        btns.pack(fill='x', pady=(12, 0))
        tk.Button(btns, text=i18n.t('btn.save'),
                  font=('Segoe UI', 10, 'bold'),
                  bg=colors['primary'], fg='white', bd=0, padx=14, pady=8,
                  cursor='hand2', command=self._save
                  ).pack(side='right', padx=(8, 0))
        tk.Button(btns, text=i18n.t('btn.cancel'),
                  font=('Segoe UI', 10),
                  bg=colors['border'], bd=0, padx=14, pady=8, cursor='hand2',
                  command=self.window.destroy
                  ).pack(side='right')

    def _save(self):
        try:
            p_idx = self.project_combo.current()
            r_idx = self.role_combo.current()
            if p_idx < 0 or r_idx < 0:
                raise ValueError("Select project and role.")
            project_id = self._project_choices[p_idx][1]
            project_role = self._role_choices[r_idx][1]
            auth.grant_project_access(self.user_id, project_id, project_role)
            self.saved = True
            self.window.destroy()
        except Exception as e:
            self.error_label.configure(text=str(e))
