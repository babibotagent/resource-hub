"""
Projects View - CRUD de Projetos
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
import database as db


class ProjectsView:
    def __init__(self, parent, colors):
        self.parent = parent
        self.colors = colors
        self.frame = tk.Frame(parent, bg=colors['background'])
        self.frame.pack(fill='both', expand=True)
        self._build()
        self._load_projects()
    
    def _build(self):
        # Header
        header = tk.Frame(self.frame, bg=self.colors['background'])
        header.pack(fill='x', padx=30, pady=(25, 15))
        
        title_frame = tk.Frame(header, bg=self.colors['background'])
        title_frame.pack(side='left')
        
        tk.Label(title_frame, text="Projetos",
                font=('Segoe UI', 24, 'bold'),
                bg=self.colors['background'],
                fg=self.colors['text']).pack(anchor='w')
        
        tk.Label(title_frame, text="Gerencie todos os projetos da organização",
                font=('Segoe UI', 10),
                bg=self.colors['background'],
                fg=self.colors['text_light']).pack(anchor='w')
        
        # Botões de ação
        actions = tk.Frame(header, bg=self.colors['background'])
        actions.pack(side='right')
        
        tk.Button(actions, text="➕ Novo Projeto",
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
        
        # Treeview
        columns = ('id', 'name', 'client', 'manager', 'start', 'end', 'budget', 'status', 'priority')
        self.tree = ttk.Treeview(table_container, columns=columns, show='headings')
        
        self.tree.heading('id', text='ID')
        self.tree.heading('name', text='Nome do Projeto')
        self.tree.heading('client', text='Cliente')
        self.tree.heading('manager', text='Gerente')
        self.tree.heading('start', text='Início')
        self.tree.heading('end', text='Fim')
        self.tree.heading('budget', text='Orçamento')
        self.tree.heading('status', text='Status')
        self.tree.heading('priority', text='Prioridade')
        
        self.tree.column('id', width=50, anchor='center')
        self.tree.column('name', width=220, anchor='w')
        self.tree.column('client', width=140, anchor='w')
        self.tree.column('manager', width=140, anchor='w')
        self.tree.column('start', width=100, anchor='center')
        self.tree.column('end', width=100, anchor='center')
        self.tree.column('budget', width=130, anchor='e')
        self.tree.column('status', width=120, anchor='center')
        self.tree.column('priority', width=100, anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_container, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side='right', fill='y')
        self.tree.pack(fill='both', expand=True)
        
        # Double-click para editar
        self.tree.bind('<Double-1>', lambda e: self._edit_selected())
    
    def _load_projects(self):
        """Carrega os projetos na tabela"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        projects = db.get_all_projects()
        for p in projects:
            self.tree.insert('', 'end', values=(
                p['id'],
                p['name'],
                p['client'] or '-',
                p['manager'] or '-',
                p['start_date'] or '-',
                p['end_date'] or '-',
                f"R$ {p['budget']:,.2f}",
                p['status'],
                p['priority']
            ))
    
    def _open_form(self, project=None):
        """Abre formulário de cadastro/edição"""
        ProjectForm(self.frame, self.colors, project, self._load_projects)
    
    def _edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione um projeto para editar")
            return
        
        item = self.tree.item(selected[0])
        project_id = item['values'][0]
        project = db.get_project(project_id)
        if project:
            self._open_form(project)
    
    def _delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione um projeto para excluir")
            return
        
        item = self.tree.item(selected[0])
        project_id = item['values'][0]
        project_name = item['values'][1]
        
        if messagebox.askyesno("Confirmar exclusão",
                              f"Deseja realmente excluir o projeto '{project_name}'?\n\n"
                              "Todas as alocações relacionadas também serão excluídas."):
            db.delete_project(project_id)
            self._load_projects()
            messagebox.showinfo("Sucesso", "Projeto excluído com sucesso!")


class ProjectForm:
    """Formulário modal para criar/editar projeto"""
    
    def __init__(self, parent, colors, project, callback):
        self.colors = colors
        self.project = project
        self.callback = callback
        
        self.window = tk.Toplevel(parent)
        self.window.title("Editar Projeto" if project else "Novo Projeto")
        self.window.geometry("550x650")
        self.window.configure(bg=colors['background'])
        self.window.transient(parent)
        self.window.grab_set()
        
        # Centraliza
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 275
        y = (self.window.winfo_screenheight() // 2) - 325
        self.window.geometry(f"+{x}+{y}")
        
        self._build()
        
        if project:
            self._fill_form()
    
    def _build(self):
        # Header
        header = tk.Frame(self.window, bg=self.colors['primary'], height=70)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header,
                text="Editar Projeto" if self.project else "Novo Projeto",
                font=('Segoe UI', 16, 'bold'),
                bg=self.colors['primary'], fg='white').pack(pady=20)
        
        # Form scrollável
        canvas = tk.Canvas(self.window, bg=self.colors['background'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.window, orient='vertical', command=canvas.yview)
        form_frame = tk.Frame(canvas, bg=self.colors['background'])
        
        form_frame.bind('<Configure>',
                       lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=form_frame, anchor='nw', width=540)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        scrollbar.pack(side='right', fill='y')
        
        # Campos
        self.entries = {}
        
        fields = [
            ('name', 'Nome do Projeto*', 'entry'),
            ('description', 'Descrição', 'text'),
            ('client', 'Cliente', 'entry'),
            ('manager', 'Gerente Responsável', 'entry'),
            ('start_date', 'Data de Início (AAAA-MM-DD)', 'entry'),
            ('end_date', 'Data de Término (AAAA-MM-DD)', 'entry'),
            ('budget', 'Orçamento (R$)', 'entry'),
            ('status', 'Status', 'combo', ['Planejamento', 'Em Andamento', 'Pausado', 'Concluído', 'Cancelado']),
            ('priority', 'Prioridade', 'combo', ['Baixa', 'Média', 'Alta', 'Crítica']),
        ]
        
        for field in fields:
            field_frame = tk.Frame(form_frame, bg=self.colors['background'])
            field_frame.pack(fill='x', padx=20, pady=8)
            
            tk.Label(field_frame, text=field[1],
                    font=('Segoe UI', 10, 'bold'),
                    bg=self.colors['background'],
                    fg=self.colors['text']).pack(anchor='w')
            
            if field[2] == 'entry':
                entry = tk.Entry(field_frame, font=('Segoe UI', 10),
                               bg='white', relief='solid', bd=1)
                entry.pack(fill='x', pady=(5, 0), ipady=6)
                self.entries[field[0]] = entry
            elif field[2] == 'text':
                entry = tk.Text(field_frame, font=('Segoe UI', 10), height=3,
                              bg='white', relief='solid', bd=1)
                entry.pack(fill='x', pady=(5, 0))
                self.entries[field[0]] = entry
            elif field[2] == 'combo':
                entry = ttk.Combobox(field_frame, values=field[3],
                                    font=('Segoe UI', 10), state='readonly')
                entry.pack(fill='x', pady=(5, 0), ipady=4)
                entry.set(field[3][0])
                self.entries[field[0]] = entry
        
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
    
    def _fill_form(self):
        """Preenche o form com dados do projeto"""
        self.entries['name'].insert(0, self.project['name'] or '')
        if self.project['description']:
            self.entries['description'].insert('1.0', self.project['description'])
        self.entries['client'].insert(0, self.project['client'] or '')
        self.entries['manager'].insert(0, self.project['manager'] or '')
        self.entries['start_date'].insert(0, self.project['start_date'] or '')
        self.entries['end_date'].insert(0, self.project['end_date'] or '')
        self.entries['budget'].insert(0, str(self.project['budget'] or 0))
        self.entries['status'].set(self.project['status'] or 'Planejamento')
        self.entries['priority'].set(self.project['priority'] or 'Média')
    
    def _save(self):
        """Salva o projeto"""
        try:
            name = self.entries['name'].get().strip()
            if not name:
                messagebox.showerror("Erro", "O nome do projeto é obrigatório")
                return
            
            description = self.entries['description'].get('1.0', 'end').strip()
            client = self.entries['client'].get().strip()
            manager = self.entries['manager'].get().strip()
            start_date = self.entries['start_date'].get().strip() or None
            end_date = self.entries['end_date'].get().strip() or None
            
            try:
                budget = float(self.entries['budget'].get() or 0)
            except ValueError:
                messagebox.showerror("Erro", "Orçamento deve ser um número")
                return
            
            status = self.entries['status'].get()
            priority = self.entries['priority'].get()
            
            if self.project:
                db.update_project(self.project['id'], name, description, client, manager,
                                 start_date, end_date, budget, status, priority)
                messagebox.showinfo("Sucesso", "Projeto atualizado com sucesso!")
            else:
                db.add_project(name, description, client, manager,
                              start_date, end_date, budget, status, priority)
                messagebox.showinfo("Sucesso", "Projeto criado com sucesso!")
            
            self.callback()
            self.window.destroy()
        
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar: {str(e)}")
