"""
Dashboard view - reads the new 12-table schema and renders KPI cards plus
small lists for project / invoice status, top projects by budget usage,
and recent risks. All labels go through the i18n module so the same
widget renders in English or French depending on the global language.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import i18n
import queries


def _fmt_eur(value):
    if value is None:
        return '-'
    return f"EUR {value:,.0f}"


def _fmt_pct(value):
    if value is None:
        return '-'
    return f"{value:.1f}%"


class DashboardView(tk.Frame):
    """A self-contained dashboard widget."""

    def __init__(self, parent, colors):
        super().__init__(parent, bg=colors['background'])
        self.colors = colors
        self.pack(fill='both', expand=True)

        # Re-render when the language changes.
        i18n.add_listener(self._on_language_change)
        self.bind('<Destroy>', lambda e: i18n.remove_listener(self._on_language_change))

        self._render()

    def _on_language_change(self, _new_lang):
        for child in self.winfo_children():
            child.destroy()
        self._render()

    def _render(self):
        try:
            kpis            = queries.dashboard_kpis()
            by_status       = queries.projects_by_status()
            invoices_status = queries.invoices_by_status()
            top_budget      = queries.top_projects_by_budget_usage()
            risks           = queries.recent_risks()
        except Exception as exc:
            self._render_error(str(exc))
            return

        # Header
        header = tk.Frame(self, bg=self.colors['background'])
        header.pack(fill='x', padx=24, pady=(20, 6))
        tk.Label(header, text=i18n.t('dash.title'),
                 font=('Segoe UI', 22, 'bold'),
                 bg=self.colors['background'],
                 fg=self.colors['text']).pack(anchor='w')
        tk.Label(header, text=i18n.t('dash.subtitle'),
                 font=('Segoe UI', 11),
                 bg=self.colors['background'],
                 fg=self.colors['text_light']).pack(anchor='w', pady=(2, 0))

        # KPI grid
        kpi_grid = tk.Frame(self, bg=self.colors['background'])
        kpi_grid.pack(fill='x', padx=24, pady=10)

        kpi_specs = [
            ('dash.kpi.projects',
             f"{kpis['projects']}",
             f"{kpis['active_projects']} {i18n.t('dash.kpi.active_projects').lower()}",
             self.colors['primary']),
            ('dash.kpi.tasks',
             f"{kpis['tasks']}",
             f"{kpis['open_tasks']} {i18n.t('dash.kpi.open_tasks').lower()}",
             '#0ea5e9'),
            ('dash.kpi.employees',
             f"{kpis['employees']}",
             f"+ {kpis['externals']} {i18n.t('dash.kpi.externals').lower()}",
             '#10b981'),
            ('dash.kpi.customers',
             f"{kpis['customers']}",
             '',
             '#a855f7'),
            ('dash.kpi.total_budget',
             _fmt_eur(kpis['total_budget']),
             f"{i18n.t('dash.kpi.budget_used_pct')}: {_fmt_pct(kpis['budget_used_pct'])}",
             self.colors['warning']),
            ('dash.kpi.outstanding_amount',
             _fmt_eur(kpis['outstanding_amount']),
             f"{kpis['invoices']} {i18n.t('dash.kpi.invoices').lower()}",
             self.colors['danger']),
        ]
        for idx, (key, big, small, accent) in enumerate(kpi_specs):
            self._kpi_card(kpi_grid, i18n.t(key), big, small, accent).grid(
                row=idx // 3, column=idx % 3, padx=8, pady=8, sticky='nsew')
        for c in range(3):
            kpi_grid.columnconfigure(c, weight=1)

        # Two-column section
        cols = tk.Frame(self, bg=self.colors['background'])
        cols.pack(fill='both', expand=True, padx=24, pady=10)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        self._status_card(
            cols, i18n.t('dash.section.projects_status'),
            [(i18n.t(f"status.{r['status']}"), r['count'], None) for r in by_status],
        ).grid(row=0, column=0, padx=8, pady=8, sticky='nsew')

        self._status_card(
            cols, i18n.t('dash.section.invoices_status'),
            [(i18n.t(f"invoice.{r['status']}"), r['count'], _fmt_eur(r['amount']))
             for r in invoices_status],
        ).grid(row=0, column=1, padx=8, pady=8, sticky='nsew')

        self._table_card(
            cols, i18n.t('dash.section.top_budget'),
            [
                (
                    p['project_code'],
                    p['project_name'],
                    p['customer_name'] or '-',
                    _fmt_eur(p['budget']),
                    _fmt_pct(p['pct_spent']),
                )
                for p in top_budget
            ],
            ['Code', i18n.t('nav.projects'), i18n.t('nav.customers'),
             i18n.t('dash.kpi.total_budget'), '%'],
        ).grid(row=1, column=0, padx=8, pady=8, sticky='nsew')

        risk_rows = []
        for r in risks:
            desc = r['description']
            if len(desc) > 55:
                desc = desc[:55] + '...'
            prob = i18n.t(f"priority.{r['probability']}")[:1] if r['probability'] else '-'
            imp  = i18n.t(f"priority.{r['impact']}")[:1] if r['impact'] else '-'
            risk_rows.append((
                r['project_code'],
                desc,
                f"{prob}/{imp}",
                i18n.t(f"risk.{r['status']}"),
                r['identified_date'] or '',
            ))
        self._table_card(
            cols, i18n.t('dash.section.recent_risks'), risk_rows,
            ['Code', i18n.t('nav.risks'), 'P/I', 'Status', 'Date'],
        ).grid(row=1, column=1, padx=8, pady=8, sticky='nsew')

        cols.rowconfigure(0, weight=0)
        cols.rowconfigure(1, weight=1)

    def _kpi_card(self, parent, title, big, small, accent):
        card = tk.Frame(parent, bg=self.colors['surface'],
                        highlightbackground=self.colors['border'],
                        highlightthickness=1)
        strip = tk.Frame(card, bg=accent, width=4)
        strip.pack(side='left', fill='y')
        body = tk.Frame(card, bg=self.colors['surface'])
        body.pack(side='left', fill='both', expand=True, padx=14, pady=12)
        tk.Label(body, text=title, font=('Segoe UI', 10),
                 bg=self.colors['surface'], fg=self.colors['text_light']
                 ).pack(anchor='w')
        tk.Label(body, text=big, font=('Segoe UI', 22, 'bold'),
                 bg=self.colors['surface'], fg=self.colors['text']
                 ).pack(anchor='w', pady=(2, 0))
        if small:
            tk.Label(body, text=small, font=('Segoe UI', 9),
                     bg=self.colors['surface'], fg=self.colors['text_light']
                     ).pack(anchor='w', pady=(2, 0))
        return card

    def _status_card(self, parent, title, rows):
        card = tk.Frame(parent, bg=self.colors['surface'],
                        highlightbackground=self.colors['border'], highlightthickness=1)
        tk.Label(card, text=title, font=('Segoe UI', 11, 'bold'),
                 bg=self.colors['surface'], fg=self.colors['text']
                 ).pack(anchor='w', padx=14, pady=(12, 6))
        for label, count, extra in rows:
            row = tk.Frame(card, bg=self.colors['surface'])
            row.pack(fill='x', padx=14, pady=2)
            tk.Label(row, text=label, font=('Segoe UI', 10),
                     bg=self.colors['surface'], fg=self.colors['text']
                     ).pack(side='left')
            right = tk.Frame(row, bg=self.colors['surface'])
            right.pack(side='right')
            if extra:
                tk.Label(right, text=extra, font=('Segoe UI', 9),
                         bg=self.colors['surface'], fg=self.colors['text_light']
                         ).pack(side='left', padx=(0, 8))
            tk.Label(right, text=str(count), font=('Segoe UI', 10, 'bold'),
                     bg=self.colors['surface'], fg=self.colors['text']
                     ).pack(side='left')
        tk.Frame(card, bg=self.colors['surface'], height=8).pack()
        return card

    def _table_card(self, parent, title, rows, headers):
        card = tk.Frame(parent, bg=self.colors['surface'],
                        highlightbackground=self.colors['border'], highlightthickness=1)
        tk.Label(card, text=title, font=('Segoe UI', 11, 'bold'),
                 bg=self.colors['surface'], fg=self.colors['text']
                 ).pack(anchor='w', padx=14, pady=(12, 6))
        if not rows:
            tk.Label(card, text=i18n.t('common.empty'), font=('Segoe UI', 10),
                     bg=self.colors['surface'], fg=self.colors['text_light']
                     ).pack(padx=14, pady=10, anchor='w')
            return card
        tree = ttk.Treeview(card, columns=headers, show='headings',
                            height=min(len(rows), 6))
        for h in headers:
            tree.heading(h, text=h)
            tree.column(h, anchor='w', width=110, stretch=True)
        for r in rows:
            tree.insert('', 'end', values=r)
        tree.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        return card

    def _render_error(self, msg):
        tk.Label(self, text=f"{i18n.t('common.error')}: {msg}",
                 font=('Segoe UI', 11),
                 bg=self.colors['background'],
                 fg=self.colors['danger']).pack(padx=24, pady=24)
