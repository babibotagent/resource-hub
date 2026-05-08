"""
Generic CRUD view: a single Tk widget that works for any table given a config
dict.  Drives every "simple" management screen (Customers, Employees,
Externals, Knowledge, Departments, Projects, Tasks, Assignments, Time entries,
Risks, Invoices) without us having to write 12 copy-pasted views.

Field types supported in form_fields:
    text, textarea, int, real, date, enum, fk

For 'fk' fields the config provides a callable returning [(label, id), ...].
For 'enum' fields the config provides the list of allowed string values.
"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import auth
from database import get_connection


class CrudView(tk.Frame):
    def __init__(self, parent, colors, config):
        super().__init__(parent, bg=colors['background'])
        self.colors = colors
        self.config_dict = config
        self.pack(fill='both', expand=True)
        self._render()

    # ------------------------------------------------------------------ render
    def _render(self):
        for child in self.winfo_children():
            child.destroy()

        # Header
        header = tk.Frame(self, bg=self.colors['background'])
        header.pack(fill='x', padx=24, pady=(20, 6))
        tk.Label(header, text=self.config_dict['title'],
                 font=('Segoe UI', 22, 'bold'),
                 bg=self.colors['background'],
                 fg=self.colors['text']).pack(anchor='w')
        tk.Label(header, text=self.config_dict.get('subtitle', ''),
                 font=('Segoe UI', 11),
                 bg=self.colors['background'],
                 fg=self.colors['text_light']).pack(anchor='w', pady=(2, 0))

        # Action bar
        bar = tk.Frame(self, bg=self.colors['background'])
        bar.pack(fill='x', padx=24, pady=(8, 4))
        can_edit = self._can_edit()
        if can_edit:
            self._btn(bar, '+ New', self._on_new, primary=True
                      ).pack(side='left', padx=(0, 6))
            self._btn(bar, 'Edit', self._on_edit
                      ).pack(side='left', padx=6)
            self._btn(bar, 'Delete', self._on_delete, danger=True
                      ).pack(side='left', padx=6)
        self._btn(bar, 'Refresh', self._refresh
                  ).pack(side='right')

        # Table
        tbl_frame = tk.Frame(self, bg=self.colors['surface'],
                             highlightbackground=self.colors['border'],
                             highlightthickness=1)
        tbl_frame.pack(fill='both', expand=True, padx=24, pady=(8, 16))

        cols = [c['key'] for c in self.config_dict['list_columns']]
        self.tree = ttk.Treeview(tbl_frame, columns=cols, show='headings')
        for col_def in self.config_dict['list_columns']:
            self.tree.heading(col_def['key'], text=col_def['header'])
            self.tree.column(
                col_def['key'],
                width=col_def.get('width', 130),
                anchor=col_def.get('anchor', 'w'),
                stretch=True,
            )
        vscroll = ttk.Scrollbar(tbl_frame, orient='vertical',
                                command=self.tree.yview)
        self.tree.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side='right', fill='y')
        self.tree.pack(fill='both', expand=True)
        if can_edit:
            self.tree.bind('<Double-1>', lambda e: self._on_edit())

        self._refresh()

    # ------------------------------------------------------------------ helpers
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

    def _can_edit(self):
        permission = self.config_dict.get('edit_permission')
        if permission is None:
            return True
        return auth.has_permission(permission)

    # ------------------------------------------------------------------ data
    def _refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        rows = self._fetch_rows()
        list_keys = [c['key'] for c in self.config_dict['list_columns']]
        formatters = {c['key']: c.get('format') for c in self.config_dict['list_columns']}
        for r in rows:
            values = []
            for k in list_keys:
                raw = r.get(k)
                fmt = formatters.get(k)
                if fmt:
                    values.append(fmt(raw, r))
                elif raw is None:
                    values.append('-')
                else:
                    values.append(raw)
            self.tree.insert('', 'end', iid=str(r[self.config_dict['pk']]),
                             values=values)

    def _fetch_rows(self):
        sql = self.config_dict['list_sql']
        params = ()
        if self.config_dict.get('project_scoped'):
            ids = auth.visible_project_ids()
            if ids is None:
                pass  # admin
            elif not ids:
                return []
            else:
                placeholders = ','.join('?' for _ in ids)
                sql += f" {self.config_dict['project_filter_clause']} "
                sql = sql.replace('__IDS__', placeholders)
                params = tuple(ids)
        sql += ' ' + self.config_dict.get('list_order_by', '')
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return int(sel[0])

    def _fetch_one(self, pk_value):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT * FROM {self.config_dict['table']} "
                f"WHERE {self.config_dict['pk']} = ?", (pk_value,))
            row = cur.fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------ events
    def _on_new(self):
        FormDialog.run(self.winfo_toplevel(), self.colors,
                       self.config_dict, existing=None,
                       on_save=self._do_insert)
        self._refresh()

    def _on_edit(self):
        pk_val = self._selected_id()
        if pk_val is None:
            return
        existing = self._fetch_one(pk_val)
        if not existing:
            return
        FormDialog.run(self.winfo_toplevel(), self.colors,
                       self.config_dict, existing=existing,
                       on_save=lambda d: self._do_update(pk_val, d))
        self._refresh()

    def _on_delete(self):
        pk_val = self._selected_id()
        if pk_val is None:
            return
        if not messagebox.askyesno('Confirm',
                                   f"Delete this {self.config_dict['singular']}?"):
            return
        try:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"DELETE FROM {self.config_dict['table']} "
                    f"WHERE {self.config_dict['pk']} = ?", (pk_val,))
            self._refresh()
        except Exception as exc:
            messagebox.showerror('Error', str(exc))

    def _do_insert(self, data):
        cols, vals, params = [], [], []
        for f in self.config_dict['form_fields']:
            cols.append(f['key'])
            vals.append('?')
            params.append(data.get(f['key']))
        # auto-fill created_at if needed
        for col in self.config_dict.get('auto_now_fields', []):
            cols.append(col)
            vals.append('?')
            params.append(datetime.utcnow().strftime('%Y-%m-%d'))
        sql = (f"INSERT INTO {self.config_dict['table']} "
               f"({', '.join(cols)}) VALUES ({', '.join(vals)})")
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)

    def _do_update(self, pk_val, data):
        sets, params = [], []
        for f in self.config_dict['form_fields']:
            sets.append(f"{f['key']} = ?")
            params.append(data.get(f['key']))
        params.append(pk_val)
        sql = (f"UPDATE {self.config_dict['table']} SET {', '.join(sets)} "
               f"WHERE {self.config_dict['pk']} = ?")
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)


# ===========================================================================
# Generic form dialog
# ===========================================================================
class FormDialog:
    @classmethod
    def run(cls, root, colors, config, *, existing, on_save):
        d = cls(root, colors, config, existing, on_save)
        root.wait_window(d.window)
        return d.saved

    def __init__(self, root, colors, config, existing, on_save):
        self.colors = colors
        self.config = config
        self.existing = existing or {}
        self.on_save = on_save
        self.saved = False
        self.entries = {}            # field_key -> widget
        self.fk_choices = {}         # field_key -> [(label, id)]

        self.window = tk.Toplevel(root)
        self.window.title(('Edit ' if existing else 'New ') + config['singular'])
        self.window.configure(bg=colors['surface'])
        self.window.geometry('520x640')
        self.window.transient(root)
        self.window.grab_set()

        # Scrollable body
        outer = tk.Frame(self.window, bg=colors['surface'])
        outer.pack(fill='both', expand=True)
        canvas = tk.Canvas(outer, bg=colors['surface'], highlightthickness=0)
        scroll = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        body = tk.Frame(canvas, bg=colors['surface'])
        body.bind('<Configure>',
                  lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=body, anchor='nw', width=500)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        scroll.pack(side='right', fill='y')

        title = ('Edit ' if existing else 'New ') + config['singular']
        tk.Label(body, text=title, font=('Segoe UI', 14, 'bold'),
                 bg=colors['surface'], fg=colors['text']
                 ).pack(anchor='w', padx=16, pady=(8, 16))

        for field in config['form_fields']:
            self._build_field(body, field)

        self.error_label = tk.Label(body, text='', font=('Segoe UI', 9),
                                    bg=colors['surface'], fg=colors['danger'],
                                    wraplength=460, justify='left')
        self.error_label.pack(anchor='w', padx=16, pady=(8, 0))

        # Buttons
        btns = tk.Frame(self.window, bg=colors['surface'])
        btns.pack(fill='x', padx=20, pady=12)
        tk.Button(btns, text='Save', font=('Segoe UI', 10, 'bold'),
                  bg=colors['primary'], fg='white', bd=0,
                  padx=18, pady=8, cursor='hand2', command=self._save
                  ).pack(side='right', padx=(8, 0))
        tk.Button(btns, text='Cancel', font=('Segoe UI', 10),
                  bg=colors['border'], bd=0, padx=18, pady=8, cursor='hand2',
                  command=self.window.destroy
                  ).pack(side='right')

    # ------------------------------------------------------------------ widgets
    def _build_field(self, parent, field):
        row = tk.Frame(parent, bg=self.colors['surface'])
        row.pack(fill='x', padx=16, pady=4)
        label_txt = field['label']
        if field.get('required'):
            label_txt += ' *'
        tk.Label(row, text=label_txt, font=('Segoe UI', 9, 'bold'),
                 bg=self.colors['surface'], fg=self.colors['text']
                 ).pack(anchor='w', pady=(4, 2))

        ftype = field['type']
        key = field['key']
        existing_val = self.existing.get(key)

        if ftype == 'textarea':
            w = tk.Text(row, font=('Segoe UI', 10), height=3,
                        bg='white', relief='solid', bd=1)
            w.pack(fill='x', pady=(0, 4))
            if existing_val:
                w.insert('1.0', str(existing_val))
            self.entries[key] = ('text', w)
        elif ftype == 'enum':
            var = tk.StringVar(value=existing_val or
                               (field.get('default') or field['values'][0]))
            cb = ttk.Combobox(row, textvariable=var, state='readonly',
                              values=field['values'])
            cb.pack(fill='x', pady=(0, 4))
            self.entries[key] = ('enum', var)
        elif ftype == 'fk':
            choices = field['choices_fn']()
            if field.get('nullable'):
                choices = [('-', None)] + list(choices)
            self.fk_choices[key] = choices
            var = tk.StringVar()
            cb = ttk.Combobox(row, textvariable=var, state='readonly',
                              values=[c[0] for c in choices])
            cb.pack(fill='x', pady=(0, 4))
            # pre-select existing value
            sel_idx = 0
            for i, (_label, val) in enumerate(choices):
                if val == existing_val:
                    sel_idx = i
                    break
            if choices:
                cb.current(sel_idx)
            self.entries[key] = ('fk', cb)
        else:  # text, int, real, date
            w = tk.Entry(row, font=('Segoe UI', 10),
                         bg='white', relief='solid', bd=1)
            w.pack(fill='x', ipady=4, pady=(0, 4))
            if existing_val is not None:
                w.insert(0, str(existing_val))
            self.entries[key] = (ftype, w)

    # ------------------------------------------------------------------ save
    def _save(self):
        try:
            data = {}
            for field in self.config['form_fields']:
                key = field['key']
                kind, widget = self.entries[key]
                ftype = field['type']
                if ftype == 'textarea':
                    raw = widget.get('1.0', 'end').strip()
                    data[key] = raw or None
                elif ftype == 'enum':
                    data[key] = widget.get() or None
                elif ftype == 'fk':
                    idx = widget.current()
                    choices = self.fk_choices[key]
                    data[key] = choices[idx][1] if idx >= 0 else None
                else:
                    raw = widget.get().strip()
                    if not raw:
                        data[key] = None
                    elif ftype == 'int':
                        data[key] = int(raw)
                    elif ftype == 'real':
                        data[key] = float(raw.replace(',', '.'))
                    else:
                        data[key] = raw
                if field.get('required') and (data[key] is None or data[key] == ''):
                    raise ValueError(f"{field['label']} is required")
            self.on_save(data)
            self.saved = True
            self.window.destroy()
        except Exception as exc:
            self.error_label.configure(text=str(exc))
