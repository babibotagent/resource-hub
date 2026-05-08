"""
Allocations View - CRUD de Alocações de recursos em projetos
"""
import tkinter as tk
from tkinter import ttk, messagebox
import database as db


class AllocationsView:
    def __init__(self, parent, colors):
        self.parent = parent
        self.colors = colors
        self.frame = tk.Frame(parent, bg=colors['background'])
        self.frame.pack(fill='both', expand=True)
        self._build()
        self._load_allocations()
    
    def _build(self):
        # Header
        header = tk.Frame(self.frame, bg=self.colors['background'])
        header.pack(fill='x', padx=30, pady=(25, 15))
        
        title_frame = tk.Frame(header, bg=self.colors['background'])
        title_frame.pack(side='left')
        
        tk.Label(title_frame, text="Alocações",
                font=('Segoe UI', 24, 'bold'),
                bg=self.colors['background'],
                fg=self.colors['text']).pack(anchor='w')
        
        tk.Label(title_frame, text="Alocação de recursos em projetos (Plan vs Actual)",
                font=('Segoe UI', 10),
                bg=self.colors['background'],
                fg=self.colors['text_light']).pack(anchor='w')
        
        actions = tk.Frame(header, bg=self.colors['background'])
        actions.pack(side='right')
        
        tk.Button(actions, text="➕ Nova Alocação",
                 font=('Segoe UI', 10, 'bold'),
                 bg=self.colors['primary'], fg='white',
                 bd=0, padx=20, pady=10, cursor='hand2',
                 command=self._open_form).pack(side='left', padx=5)
        
        tk.Button(actions, text="✏️ Editar",
                 font=('Segoe UI', 10, 'bold'),
                 bg=self.colors['warning'], fg='white',
                 bd=0, padx=20, pady=10, cursor='hand2',
                 command=self._edit_selected).pack(side='left', padx=5)
        
        tk.Button(actions, text="🗑️ Excluir",
                 font=('Segoe UI', 10, 'bold'),
                 bg=self.colors['danger'], fg='white',
                 bd=0, padx=20, pady=10, cursor='hand2',
                 command=self._delete_selected).pack(side='left', padx=5)
        
        # Container da tabela
        table_container = tk.Frame(self.frame, bg='white',
                                   highlightbackground=self.colors['border'],
                                   highlightthickness=1)
        table_container.pack(fill='both', expand=True, padx=30, pady=(0, 30))
        
        columns = ('id', 'project', 'resource', 'role', 'start', 'end', 'planned', 'actual', 'progress')
        self.tree = ttk.Treeview(table_container, columns=columns, show='headings')
        
        self.tree.heading('id', text='ID')
        self.tree.heading('project', text='Projeto')
        self.tree.heading('resource', text='Recurso')
        self.tree.heading('role', text='Função no Projeto')
        self.tree.heading('start', text='Início')
        self.tree.heading('end', text='Fim')
        self.tree.heading('planned', text='Plan. (h)')
        self.tree.heading('actual', text='Real. (h)')
        self.tree.heading('progress', text='Progresso')
        
        self.tree.column('id', width=50, anchor='center')
        self.tree.column('project', width=200, anchor='w')
        self.tree.column('resource', width=180, anchor='w')
        self.tree.column('role', width=160, anchor='w')
        self.tree.column('start', width=100, anchor='center')
        self.tree.column('end', width=100, anchor='center')
        self.tree.column('planned', width=90, anchor='center')
        self.tree.column('actual', width=90, anchor='center')
        self.tree.column('progress', width=100, anchor='center')
        
        scrollbar = ttk.Scrollbar(table_container, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side='right', fill='y')
        self.tree.pack(fill='both', expand=True)
        
        self.tree.bind('<Double-1>', lambda e: self._edit_selected())
    
    def _load_allocations(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        allocations = db.get_all_allocations()
        for a in allocations:
            planned = a['planned_hours'] or 0
            actual = a['actual_hours'] or 0
            progress = (actual / planned * 100) if planned > 0 else 0
            
            self.tree.insert('', 'end', values=(
                a['id'],
                a['project_name'],
                a['resource_name'],
                a['role_in_project'] or '-',
                a['start_date'],
                a['end_date'],
                f"{planned:.0f}",
                f"{actual:.0f}",
                f"{progress:.1f}%"
            ))
    
    def _open_form(self, allocation=None):
        AllocationForm(self.frame, self.colors, allocation, self._load_allocations)
    
    def _edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione uma alocação para editar")
            return
        
        item = self.tree.item(selected[0])
        allocation_id = item['values'][0]
        
        # Buscar alocação completa
        allocations = db.get_all_allocations()
        allocation = next((a for a in allocations if a['id'] == allocation_id), None)
        if allocation:
            self._open_form(allocation)
    
    def _delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione uma alocação para excluir")
            return
        
        item = self.tree.item(selected[0])
        allocation_id = item['values'][0]
        
        if messagebox.askyesno("Confirmar exclusão",
                              "Deseja realmente excluir esta alocação?"):
            db.delete_allocation(allocation_id)
            self._load_allocations()
            messagebox.showinfo("Sucesso", "Alocação excluída!")


class AllocationForm:
    """Formulário de cadastro/edição de alocação"""
    
    def __init__(self, parent, colors, allocation, callback):
        self.colors = colors
        self.allocation = allocation
        self.callback = callback
        
        self.window = tk.Toplevel(parent)
        self.window.title("Editar Alocação" if allocation else "Nova Alocação")
        self.window.geometry("550x650")
        self.window.configure(bg=colors['background'])
        self.window.transient(parent)
        self.window.grab_set()
        
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 275
        y = (self.window.winfo_screenheight() // 2) - 325
        self.window.geometry(f"+{x}+{y}")
        
        # Carregar projetos e recursos
        self.projects = db.get_all_projects()
        self.resources = db.get_all_resources()
        
        self._build()
        
        if allocation:
            self._fill_form()
    
    def _build(self):
        header = tk.Frame(self.window, bg=self.colors['primary'], height=70)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header,
                text="Editar Alocação" if self.allocation else "Nova Alocação",
                font=('Segoe UI', 16, 'bold'),
                bg=self.colors['primary'], fg='white').pack(pady=20)
        
        canvas = tk.Canvas(self.window, bg=self.colors['background'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.window, orient='vertical', command=canvas.yview)
        form_frame = tk.Frame(canvas, bg=self.colors['background'])
        
        form_frame.bind('<Configure>',
                       lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=form_frame, anchor='nw', width=540)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        scrollbar.pack(side='right', fill='y')
        
        self.entries = {}
        
        # Projeto
        self._create_label(form_frame, "Projeto*")
        project_names = [f"{p['id']} - {p['name']}" for p in self.projects]
        self.entries['project'] = ttk.Combobox(form_frame, values=project_names,
                                                font=('Segoe UI', 10), state='readonly')
        self.entries['project'].pack(fill='x', padx=20, pady=(5, 10), ipady=4)
        
        # Recurso
        self._create_label(form_frame, "Recurso*")
        resource_names = [f"{r['id']} - {r['name']}" for r in self.resources]
        self.entries['resource'] = ttk.Combobox(form_frame, values=resource_names,
                                                 font=('Segoe UI', 10), state='readonly')
        self.entries['resource'].pack(fill='x', padx=20, pady=(5, 10), ipady=4)
        
        # Função no projeto
        self._create_label(form_frame, "Função no Projeto")
        self.entries['role'] = tk.Entry(form_frame, font=('Segoe UI', 10),
                                        bg='white', relief='solid', bd=1)
        self.entries['role'].pack(fill='x', padx=20, pady=(5, 10), ipady=6)
        
        # Datas
        date_frame = tk.Frame(form_frame, bg=self.colors['background'])
        date_frame.pack(fill='x', padx=20, pady=(5, 10))
        
        start_frame = tk.Frame(date_frame, bg=self.colors['background'])
        start_frame.pack(side='left', fill='x', expand=True, padx=(0, 5))
        tk.Label(start_frame, text="Data Início* (AAAA-MM-DD)",
                font=('Segoe UI', 10, 'bold'),
                bg=self.colors['background'], fg=self.colors['text']).pack(anchor='w')
        self.entries['start_date'] = tk.Entry(start_frame, font=('Segoe UI', 10),
                                              bg='white', relief='solid', bd=1)
        self.entries['start_date'].pack(fill='x', pady=(5, 0), ipady=6)
        
        end_frame = tk.Frame(date_frame, bg=self.colors['background'])
        end_frame.pack(side='left', fill='x', expand=True, padx=(5, 0))
        tk.Label(end_frame, text="Data Fim* (AAAA-MM-DD)",
                font=('Segoe UI', 10, 'bold'),
                bg=self.colors['background'], fg=self.colors['text']).pack(anchor='w')
        self.entries['end_date'] = tk.Entry(end_frame, font=('Segoe UI', 10),
                                            bg='white', relief='solid', bd=1)
        self.entries['end_date'].pack(fill='x', pady=(5, 0), ipady=6)
        
        # Horas
        hours_frame = tk.Frame(form_frame, bg=self.colors['background'])
        hours_frame.pack(fill='x', padx=20, pady=(5, 10))
        
        plan_frame = tk.Frame(hours_frame, bg=self.colors['background'])
        plan_frame.pack(side='left', fill='x', expand=True, padx=(0, 5))
        tk.Label(plan_frame, text="Horas Planejadas",
                font=('Segoe UI', 10, 'bold'),
                bg=self.colors['background'], fg=self.colors['text']).pack(anchor='w')
        self.entries['planned_hours'] = tk.Entry(plan_frame, font=('Segoe UI', 10),
                                                  bg='white', relief='solid', bd=1)
        self.entries['planned_hours'].pack(fill='x', pady=(5, 0), ipady=6)
        self.entries['planned_hours'].insert(0, '0')
        
        actual_frame = tk.Frame(hours_frame, bg=self.colors['background'])
        actual_frame.pack(side='left', fill='x', expand=True, padx=(5, 0))
        tk.Label(actual_frame, text="Horas Realizadas",
                font=('Segoe UI', 10, 'bold'),
                bg=self.colors['background'], fg=self.colors['text']).pack(anchor='w')
        self.entries['actual_hours'] = tk.Entry(actual_frame, font=('Segoe UI', 10),
                                                 bg='white', relief='solid', bd=1)
        self.entries['actual_hours'].pack(fill='x', pady=(5, 0), ipady=6)
        self.entries['actual_hours'].insert(0, '0')
        
        # Notas
        self._create_label(form_frame, "Observações")
        self.entries['notes'] = tk.Text(form_frame, font=('Segoe UI', 10), height=4,
                                         bg='white', relief='solid', bd=1)
        self.entries['notes'].pack(fill='x', padx=20, pady=(5, 10))
        
        # Botões
        btn_frame = tk.Frame(self.window, bg=self.colors['background'])
        btn_frame.pack(fill='x', padx=20, pady=15)
        
        tk.Button(btn_frame, text="Cancelar",
                 font=('Segoe UI', 10),
                 bg=self.colors['secondary'], fg='white',
                 bd=0, padx=20, pady=10, cursor='hand2',
                 command=self.window.destroy).pack(side='right', padx=5)
        
        tk.Button(btn_frame, text="💾 Salvar",
                 font=('Segoe UI', 10, 'bold'),
                 bg=self.colors['success'], fg='white',
                 bd=0, padx=20, pady=10, cursor='hand2',
                 command=self._save).pack(side='right', padx=5)
    
    def _create_label(self, parent, text):
        tk.Label(parent, text=text,
                font=('Segoe UI', 10, 'bold'),
                bg=self.colors['background'], fg=self.colors['text']).pack(anchor='w', padx=20)
    
    def _fill_form(self):
        # Encontrar projeto
        for i, p in enumerate(self.projects):
            if p['id'] == self.allocation['project_id']:
                self.entries['project'].current(i)
                break
        
        # Encontrar recurso
        for i, r in enumerate(self.resources):
            if r['id'] == self.allocation['resource_id']:
                self.entries['resource'].current(i)
                break
        
        self.entries['role'].insert(0, self.allocation['role_in_project'] or '')
        self.entries['start_date'].insert(0, self.allocation['start_date'] or '')
        self.entries['end_date'].insert(0, self.allocation['end_date'] or '')
        self.entries['planned_hours'].delete(0, 'end')
        self.entries['planned_hours'].insert(0, str(self.allocation['planned_hours'] or 0))
        self.entries['actual_hours'].delete(0, 'end')
        self.entries['actual_hours'].insert(0, str(self.allocation['actual_hours'] or 0))
        if self.allocation['notes']:
            self.entries['notes'].insert('1.0', self.allocation['notes'])
    
    def _save(self):
        try:
            project_str = self.entries['project'].get()
            resource_str = self.entries['resource'].get()
            
            if not project_str or not resource_str:
                messagebox.showerror("Erro", "Selecione projeto e recurso")
                return
            
            project_id = int(project_str.split(' - ')[0])
            resource_id = int(resource_str.split(' - ')[0])
            
            start_date = self.entries['start_date'].get().strip()
            end_date = self.entries['end_date'].get().strip()
            
            if not start_date or not end_date:
                messagebox.showerror("Erro", "As datas são obrigatórias")
                return
            
            try:
                planned = float(self.entries['planned_hours'].get() or 0)
                actual = float(self.entries['actual_hours'].get() or 0)
            except ValueError:
                messagebox.showerror("Erro", "Horas devem ser números")
                return
            
            role = self.entries['role'].get().strip()
            notes = self.entries['notes'].get('1.0', 'end').strip()
            
            if self.allocation:
                db.update_allocation(self.allocation['id'], project_id, resource_id,
                                    start_date, end_date, planned, actual, role, notes)
                messagebox.showinfo("Sucesso", "Alocação atualizada!")
            else:
                db.add_allocation(project_id, resource_id, start_date, end_date,
                                 planned, actual, role, notes)
                messagebox.showinfo("Sucesso", "Alocação criada!")
            
            self.callback()
            self.window.destroy()
        
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar: {str(e)}")
