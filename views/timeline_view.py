"""
Timeline View - Visualização Gantt das alocações
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
import database as db
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import matplotlib.patches as mpatches


class TimelineView:
    def __init__(self, parent, colors):
        self.parent = parent
        self.colors = colors
        self.frame = tk.Frame(parent, bg=colors['background'])
        self.frame.pack(fill='both', expand=True)
        self._build()
    
    def _build(self):
        # Header
        header = tk.Frame(self.frame, bg=self.colors['background'])
        header.pack(fill='x', padx=30, pady=(25, 15))
        
        title_frame = tk.Frame(header, bg=self.colors['background'])
        title_frame.pack(side='left')
        
        tk.Label(title_frame, text="Timeline",
                font=('Segoe UI', 24, 'bold'),
                bg=self.colors['background'],
                fg=self.colors['text']).pack(anchor='w')
        
        tk.Label(title_frame, text="Visão temporal das alocações de recursos",
                font=('Segoe UI', 10),
                bg=self.colors['background'],
                fg=self.colors['text_light']).pack(anchor='w')
        
        # Controles
        controls = tk.Frame(header, bg=self.colors['background'])
        controls.pack(side='right')
        
        tk.Label(controls, text="Visualizar:",
                font=('Segoe UI', 10),
                bg=self.colors['background']).pack(side='left', padx=5)
        
        self.view_mode = ttk.Combobox(controls,
                                      values=['Por Projeto', 'Por Recurso'],
                                      state='readonly', width=15)
        self.view_mode.set('Por Projeto')
        self.view_mode.pack(side='left', padx=5)
        self.view_mode.bind('<<ComboboxSelected>>', lambda e: self._draw_timeline())
        
        tk.Button(controls, text="🔄 Atualizar",
                 font=('Segoe UI', 9, 'bold'),
                 bg=self.colors['primary'], fg='white',
                 bd=0, padx=15, pady=8, cursor='hand2',
                 command=self._draw_timeline).pack(side='left', padx=10)
        
        # Container do gráfico
        self.chart_container = tk.Frame(self.frame, bg='white',
                                        highlightbackground=self.colors['border'],
                                        highlightthickness=1)
        self.chart_container.pack(fill='both', expand=True, padx=30, pady=(0, 30))
        
        self._draw_timeline()
    
    def _draw_timeline(self):
        """Desenha o gráfico Gantt"""
        for widget in self.chart_container.winfo_children():
            widget.destroy()
        
        allocations = db.get_all_allocations()
        
        if not allocations:
            tk.Label(self.chart_container,
                    text="Nenhuma alocação cadastrada\n\nCadastre alocações para visualizar a timeline",
                    font=('Segoe UI', 12),
                    bg='white', fg=self.colors['text_light']).pack(expand=True, pady=100)
            return
        
        # Criar figura
        fig = Figure(figsize=(14, 8), dpi=80, facecolor='white')
        ax = fig.add_subplot(111)
        
        view_by = self.view_mode.get()
        
        # Organizar dados
        if view_by == 'Por Projeto':
            # Agrupar por projeto
            grouped = {}
            for a in allocations:
                key = a['project_name']
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(a)
        else:
            # Agrupar por recurso
            grouped = {}
            for a in allocations:
                key = a['resource_name']
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(a)
        
        # Cores por categoria
        colors_palette = ['#2563eb', '#10b981', '#f59e0b', '#ef4444',
                         '#8b5cf6', '#ec4899', '#14b8a6', '#f97316',
                         '#06b6d4', '#84cc16']
        
        y_pos = 0
        y_labels = []
        legend_handles = []
        seen_categories = set()
        
        for idx, (group_name, items) in enumerate(grouped.items()):
            color = colors_palette[idx % len(colors_palette)]
            
            for item in items:
                try:
                    start = datetime.strptime(item['start_date'], '%Y-%m-%d')
                    end = datetime.strptime(item['end_date'], '%Y-%m-%d')
                    duration = (end - start).days
                    
                    # Barra principal (planejado)
                    ax.barh(y_pos, duration, left=start, height=0.6,
                           color=color, alpha=0.4, edgecolor=color, linewidth=1.5)
                    
                    # Barra de progresso (realizado)
                    planned = item['planned_hours'] or 0
                    actual = item['actual_hours'] or 0
                    progress = min(actual / planned, 1.0) if planned > 0 else 0
                    
                    if progress > 0:
                        progress_duration = duration * progress
                        ax.barh(y_pos, progress_duration, left=start, height=0.6,
                               color=color, alpha=0.9)
                    
                    # Texto sobre a barra
                    if view_by == 'Por Projeto':
                        label = f"  {item['resource_name']}"
                    else:
                        label = f"  {item['project_name']}"
                    
                    ax.text(start, y_pos, label,
                           va='center', ha='left', fontsize=8,
                           color=self.colors['text'])
                    
                    y_labels.append(group_name if y_pos == 0 or y_labels[-1] != group_name else '')
                    y_pos += 1
                except (ValueError, TypeError) as e:
                    continue
            
            if group_name not in seen_categories:
                legend_handles.append(mpatches.Patch(color=color, label=group_name))
                seen_categories.add(group_name)
        
        # Configurações do gráfico
        ax.set_yticks(range(len(y_labels)))
        ax.set_yticklabels(y_labels, fontsize=9)
        ax.invert_yaxis()
        
        # Formatar eixo X (datas)
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b/%Y'))
        ax.xaxis.set_minor_locator(mdates.WeekdayLocator())
        
        fig.autofmt_xdate(rotation=45)
        
        # Grade
        ax.grid(True, axis='x', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        
        # Estilo
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(self.colors['border'])
        ax.spines['bottom'].set_color(self.colors['border'])
        
        ax.set_xlabel('Período', fontsize=10, color=self.colors['text'])
        title_text = 'Timeline - Alocações por ' + ('Projeto' if view_by == 'Por Projeto' else 'Recurso')
        ax.set_title(title_text, fontsize=12, fontweight='bold', color=self.colors['text'], pad=15)
        
        # Legenda
        if legend_handles:
            ax.legend(handles=legend_handles, loc='upper right',
                     fontsize=8, framealpha=0.9, ncol=min(3, len(legend_handles)))
        
        # Linha do "hoje"
        today = datetime.now()
        ax.axvline(today, color=self.colors['danger'], linestyle='--',
                  linewidth=1.5, alpha=0.7, label='Hoje')
        ax.text(today, ax.get_ylim()[0], ' Hoje',
               color=self.colors['danger'], fontsize=9, fontweight='bold',
               va='top', ha='left')
        
        fig.tight_layout()
        
        # Renderizar
        canvas = FigureCanvasTkAgg(fig, self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
        
        # Legenda explicativa
        info_frame = tk.Frame(self.chart_container, bg='white')
        info_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        tk.Label(info_frame,
                text="💡 Barras transparentes: período planejado | Barras sólidas: progresso realizado | Linha tracejada vermelha: data atual",
                font=('Segoe UI', 9, 'italic'),
                bg='white', fg=self.colors['text_light']).pack()
