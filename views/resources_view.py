"""
Resources View - CRUD de Recursos
"""
import tkinter as tk
from tkinter import ttk, messagebox
import database as db


class ResourcesView:
    def __init__(self, parent, colors):
        self.parent = parent
        self.colors = colors
        self.frame = tk.Frame(parent, bg=colors['background'])
        self.frame.pack(fill='both', expand=True)
        self._build()
        self._load_resources()
    
    def _build(self):
        # Header
        header = tk.Frame(self.frame, bg=self.colors['background'])
        header.pack(fill='x', padx=30, pady=(25, 15))
        
        title_frame = tk.Frame(header, bg=self.colors['background'])
        title_frame.pack(side='left')
        
        tk.Label(title_frame, text="Recursos",
                font=('Segoe UI', 24, 'bold'),
                bg=self.colors['background'],
                fg=self.colors['text']).pack(anchor='w')
        
        tk.Label(title_frame, text="Cadastro de pessoas, equipamentos e ativos",
                font=('Segoe UI', 10),
                bg=self.colors['background'],
                fg=self.colors['text_light']).pack(anchor='w')
        
        # Botões de ação
        actions = tk.Frame(header, bg=self.colors['background'])
        actions.pack(side='right')
        
        tk.Button(actions, text="➕ Novo Recurso",
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
        columns = ('id', 'name', 'role', 'type', 'email', 'rate', 'capacity', 'status')
        self.tree = ttk.Treeview(table_container, columns=columns, show='headings')
        
        self.tree.heading('id', text='ID')
        self.tree.heading('name', text='Nome')
        self.tree.heading('role', text='Função')
        self.tree.heading('type', text='Tipo')
        self.tree.heading('email', text='Email')
        self.tree.heading('rate', text='Taxa/h')
        self.tree.heading('capacity', text='Cap. Sem.')
        self.tree.heading('status', text='Status')
        
        self.tree.column('id', width=50, anchor='center')
        self.tree.column('name', width=200, anchor='w')
        self.tree.column('role', width=180, anchor='w')
        self.tree.column('type', width=100, anchor='center')
        self.tree.column('email', width=200, anchor='w')
        self.tree.column('rate', width=100, anchor='e')
        self.tree.column('capacity', width=90, anchor='center')
        self.tree.column('status', width=100, anchor='center')
        
        scrollbar = ttk.Scrollbar(table_container, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side='right', fill='y')
        self.tree.pack(fill='both', expand=True)
        
        self.tree.bind('<Double-1>', lambda e: self._edit_selected())
    
    def _load_resources(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        resources = db.get_all_resources()
        for r in resources:
            self.tree.insert('', 'end', values=(
                r['id'],
                r['name'],
                r['role'] or '-',
                r['resource_type'] or 'Humano',
                r['email'] or '-',
                f"R$ {r['hourly_rate']:.2f}",
                f"{r['capacity_hours_week']:.0f}h",
                r['status']
            ))
    
    def _open_form(self, resource=None):
        ResourceForm(self.frame, self.colors, resource, self._load_resources)
    
    def _edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione um recurso para editar")
            return
        
        item = self.tree.item(selected[0])
        resource_id = item['values'][0]
        resource = db.get_resource(resource_id)
        if resource:
            self._open_form(resource)
    
    def _delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione um recurso para excluir")
            return
        
        item = self.tree.item(selected[0])
        resource_id = item['values'][0]
        resource_name = item['values'][1]
        
        if messagebox.askyesno("Confirmar exclusão",
                              f"Deseja realmente excluir o recurso '{resource_name}'?\n\n"
                              "Todas as alocações deste recurso também serão excluídas."):
            db.delete_resource(resource_id)
            self._load_resources()
            messagebox.showinfo("Sucesso", "Recurso excluído com sucesso!")


class ResourceForm:
    """Formulário de cadastro/edição de recurso"""
    
    def __init__(self, parent, colors, resource, callback):
        self.colors = colors
        self.resource = resource
        self.callback = callback
        
        self.window = tk.Toplevel(parent)
        self.window.title("Editar Recurso" if resource else "Novo Recurso")
        self.window.geometry("550x650")
        self.window.configure(bg=colors['background'])
        self.window.transient(parent)
        self.window.grab_set()
        
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 275
        y = (self.window.winfo_screenheight() // 2) - 325
        self.window.geometry(f"+{x}+{y}")
        
        self._build()
        
        if resource:
            self._fill_form()
    
    def _build(self):
        # Header
        header = tk.Frame(self.window, bg=self.colors['primary'], height=70)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header,
                text="Editar Recurso" if self.resource else "Novo Recurso",
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
        
        fields = [
            ('name', 'Nome*', 'entry'),
            ('role', 'Função/Cargo', 'entry'),
            ('resource_type', 'Tipo de Recurso', 'combo', ['Humano', 'Equipamento', 'Material', 'Software', 'Outro']),
            ('email', 'Email', 'entry'),
            ('hourly_rate', 'Taxa Horária (R$)', 'entry'),
            ('capacity_hours_week', 'Capacidade Semanal (horas)', 'entry'),
            ('skills', 'Habilidades (separadas por vírgula)', 'text'),
            ('status', 'Status', 'combo', ['Ativo', 'Inativo', 'Férias', 'Afastado']),
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
        self.entries['name'].insert(0, self.resource['name'] or '')
        self.entries['role'].insert(0, self.resource['role'] or '')
        self.entries['resource_type'].set(self.resource['resource_type'] or 'Humano')
        self.entries['email'].insert(0, self.resource['email'] or '')
        self.entries['hourly_rate'].insert(0, str(self.resource['hourly_rate'] or 0))
        self.entries['capacity_hours_week'].insert(0, str(self.resource['capacity_hours_week'] or 40))
        if self.resource['skills']:
            self.entries['skills'].insert('1.0', self.resource['skills'])
        self.entries['status'].set(self.resource['status'] or 'Ativo')
    
    def _save(self):
        try:
            name = self.entries['name'].get().strip()
            if not name:
                messagebox.showerror("Erro", "O nome é obrigatório")
                return
            
            role = self.entries['role'].get().strip()
            resource_type = self.entries['resource_type'].get()
            email = self.entries['email'].get().strip()
            
            try:
                hourly_rate = float(self.entries['hourly_rate'].get() or 0)
                capacity = float(self.entries['capacity_hours_week'].get() or 40)
            except ValueError:
                messagebox.showerror("Erro", "Taxa horária e capacidade devem ser números")
                return
            
            skills = self.entries['skills'].get('1.0', 'end').strip()
            status = self.entries['status'].get()
            
            if self.resource:
                db.update_resource(self.resource['id'], name, role, resource_type,
                                  email, hourly_rate, capacity, skills, status)
                messagebox.showinfo("Sucesso", "Recurso atualizado!")
            else:
                db.add_resource(name, role, resource_type, email,
                               hourly_rate, capacity, skills, status)
                messagebox.showinfo("Sucesso", "Recurso criado!")
            
            self.callback()
            self.window.destroy()
        
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar: {str(e)}")
