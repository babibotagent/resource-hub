"""
Módulo de gerenciamento do banco de dados SQLite
Gestão de Recursos de Projetos
"""
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'projects.db')


@contextmanager
def get_connection():
    """Context manager para conexão com o banco"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_database():
    """Inicializa o banco de dados criando todas as tabelas necessárias"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Tabela de Recursos (pessoas, equipamentos, etc.)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT,
                resource_type TEXT DEFAULT 'Humano',
                email TEXT,
                hourly_rate REAL DEFAULT 0,
                capacity_hours_week REAL DEFAULT 40,
                skills TEXT,
                status TEXT DEFAULT 'Ativo',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de Projetos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                client TEXT,
                manager TEXT,
                start_date DATE,
                end_date DATE,
                budget REAL DEFAULT 0,
                status TEXT DEFAULT 'Planejamento',
                priority TEXT DEFAULT 'Média',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de Alocações (recursos x projetos x horas)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS allocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                resource_id INTEGER NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                planned_hours REAL DEFAULT 0,
                actual_hours REAL DEFAULT 0,
                role_in_project TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
            )
        ''')
        
        # Tabela de Tarefas (opcional, para detalhamento)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                resource_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                start_date DATE,
                end_date DATE,
                planned_hours REAL DEFAULT 0,
                actual_hours REAL DEFAULT 0,
                status TEXT DEFAULT 'Pendente',
                progress INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE SET NULL
            )
        ''')
        
        # Tabela de Time Logs (registro de horas trabalhadas)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS time_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                allocation_id INTEGER NOT NULL,
                log_date DATE NOT NULL,
                hours REAL NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (allocation_id) REFERENCES allocations(id) ON DELETE CASCADE
            )
        ''')


# ==================== RESOURCES ====================
def add_resource(name, role, resource_type, email, hourly_rate, capacity, skills, status):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO resources (name, role, resource_type, email, hourly_rate, 
                                    capacity_hours_week, skills, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, role, resource_type, email, hourly_rate, capacity, skills, status))
        return cursor.lastrowid


def get_all_resources():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM resources ORDER BY name')
        return [dict(row) for row in cursor.fetchall()]


def get_resource(resource_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM resources WHERE id = ?', (resource_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_resource(resource_id, name, role, resource_type, email, hourly_rate, capacity, skills, status):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE resources 
            SET name=?, role=?, resource_type=?, email=?, hourly_rate=?, 
                capacity_hours_week=?, skills=?, status=?
            WHERE id=?
        ''', (name, role, resource_type, email, hourly_rate, capacity, skills, status, resource_id))


def delete_resource(resource_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM resources WHERE id = ?', (resource_id,))


# ==================== PROJECTS ====================
def add_project(name, description, client, manager, start_date, end_date, budget, status, priority):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO projects (name, description, client, manager, start_date, 
                                   end_date, budget, status, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, description, client, manager, start_date, end_date, budget, status, priority))
        return cursor.lastrowid


def get_all_projects():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM projects ORDER BY start_date DESC')
        return [dict(row) for row in cursor.fetchall()]


def get_project(project_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_project(project_id, name, description, client, manager, start_date, end_date, budget, status, priority):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE projects 
            SET name=?, description=?, client=?, manager=?, start_date=?, 
                end_date=?, budget=?, status=?, priority=?
            WHERE id=?
        ''', (name, description, client, manager, start_date, end_date, budget, status, priority, project_id))


def delete_project(project_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))


# ==================== ALLOCATIONS ====================
def add_allocation(project_id, resource_id, start_date, end_date, planned_hours, actual_hours, role_in_project, notes):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO allocations (project_id, resource_id, start_date, end_date, 
                                      planned_hours, actual_hours, role_in_project, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (project_id, resource_id, start_date, end_date, planned_hours, actual_hours, role_in_project, notes))
        return cursor.lastrowid


def get_all_allocations():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.*, p.name as project_name, r.name as resource_name, r.role as resource_role
            FROM allocations a
            JOIN projects p ON a.project_id = p.id
            JOIN resources r ON a.resource_id = r.id
            ORDER BY a.start_date DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]


def get_allocations_by_project(project_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.*, r.name as resource_name, r.role as resource_role
            FROM allocations a
            JOIN resources r ON a.resource_id = r.id
            WHERE a.project_id = ?
            ORDER BY a.start_date
        ''', (project_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_allocations_by_resource(resource_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.*, p.name as project_name
            FROM allocations a
            JOIN projects p ON a.project_id = p.id
            WHERE a.resource_id = ?
            ORDER BY a.start_date
        ''', (resource_id,))
        return [dict(row) for row in cursor.fetchall()]


def update_allocation(allocation_id, project_id, resource_id, start_date, end_date, planned_hours, actual_hours, role_in_project, notes):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE allocations 
            SET project_id=?, resource_id=?, start_date=?, end_date=?, 
                planned_hours=?, actual_hours=?, role_in_project=?, notes=?
            WHERE id=?
        ''', (project_id, resource_id, start_date, end_date, planned_hours, actual_hours, role_in_project, notes, allocation_id))


def delete_allocation(allocation_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM allocations WHERE id = ?', (allocation_id,))


# ==================== DASHBOARD STATS ====================
def get_dashboard_stats():
    """Retorna estatísticas para o dashboard"""
    with get_connection() as conn:
        cursor = conn.cursor()
        stats = {}
        
        # Total de projetos
        cursor.execute('SELECT COUNT(*) as total FROM projects')
        stats['total_projects'] = cursor.fetchone()['total']
        
        # Projetos ativos
        cursor.execute("SELECT COUNT(*) as total FROM projects WHERE status IN ('Em Andamento', 'Planejamento')")
        stats['active_projects'] = cursor.fetchone()['total']
        
        # Total de recursos
        cursor.execute("SELECT COUNT(*) as total FROM resources WHERE status = 'Ativo'")
        stats['total_resources'] = cursor.fetchone()['total']
        
        # Total de horas planejadas vs realizadas
        cursor.execute('SELECT SUM(planned_hours) as planned, SUM(actual_hours) as actual FROM allocations')
        row = cursor.fetchone()
        stats['planned_hours'] = row['planned'] or 0
        stats['actual_hours'] = row['actual'] or 0
        
        # Orçamento total
        cursor.execute('SELECT SUM(budget) as total FROM projects')
        stats['total_budget'] = cursor.fetchone()['total'] or 0
        
        # Custo realizado (horas atuais x taxa horária)
        cursor.execute('''
            SELECT SUM(a.actual_hours * r.hourly_rate) as cost
            FROM allocations a
            JOIN resources r ON a.resource_id = r.id
        ''')
        stats['actual_cost'] = cursor.fetchone()['cost'] or 0
        
        # Projetos por status
        cursor.execute('SELECT status, COUNT(*) as count FROM projects GROUP BY status')
        stats['projects_by_status'] = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # Top 5 recursos mais alocados
        cursor.execute('''
            SELECT r.name, SUM(a.planned_hours) as total_hours
            FROM allocations a
            JOIN resources r ON a.resource_id = r.id
            GROUP BY r.id, r.name
            ORDER BY total_hours DESC
            LIMIT 5
        ''')
        stats['top_resources'] = [dict(row) for row in cursor.fetchall()]
        
        return stats


def get_resource_utilization():
    """Calcula a utilização de cada recurso"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                r.id, r.name, r.capacity_hours_week,
                COALESCE(SUM(a.planned_hours), 0) as planned_hours,
                COALESCE(SUM(a.actual_hours), 0) as actual_hours
            FROM resources r
            LEFT JOIN allocations a ON r.id = a.resource_id
            WHERE r.status = 'Ativo'
            GROUP BY r.id, r.name, r.capacity_hours_week
            ORDER BY planned_hours DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]


def seed_sample_data():
    """Popula o banco com dados de exemplo (apenas se vazio)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as total FROM resources')
        if cursor.fetchone()['total'] > 0:
            return False
    
    # Recursos de exemplo
    resources_sample = [
        ('Ana Silva', 'Desenvolvedora Senior', 'Humano', 'ana@empresa.com', 85.0, 40, 'Python, React, SQL', 'Ativo'),
        ('Bruno Costa', 'Designer UX/UI', 'Humano', 'bruno@empresa.com', 70.0, 40, 'Figma, Adobe XD, Prototipagem', 'Ativo'),
        ('Carla Mendes', 'Gerente de Projetos', 'Humano', 'carla@empresa.com', 95.0, 40, 'PMP, Agile, Scrum', 'Ativo'),
        ('Daniel Rocha', 'Desenvolvedor Backend', 'Humano', 'daniel@empresa.com', 75.0, 40, 'Java, Spring, PostgreSQL', 'Ativo'),
        ('Eduarda Lima', 'QA Tester', 'Humano', 'eduarda@empresa.com', 60.0, 40, 'Selenium, Cypress, Testes', 'Ativo'),
        ('Felipe Santos', 'DevOps Engineer', 'Humano', 'felipe@empresa.com', 90.0, 40, 'AWS, Docker, Kubernetes', 'Ativo'),
    ]
    
    for r in resources_sample:
        add_resource(*r)
    
    # Projetos de exemplo
    projects_sample = [
        ('Sistema CRM', 'Desenvolvimento de CRM customizado', 'Cliente Alpha', 'Carla Mendes', 
         '2026-01-15', '2026-06-30', 250000.0, 'Em Andamento', 'Alta'),
        ('App Mobile E-commerce', 'Aplicativo iOS e Android', 'Cliente Beta', 'Carla Mendes', 
         '2026-02-01', '2026-08-31', 180000.0, 'Planejamento', 'Média'),
        ('Migração Cloud', 'Migração de infraestrutura para AWS', 'Cliente Gamma', 'Carla Mendes', 
         '2025-11-01', '2026-04-30', 120000.0, 'Em Andamento', 'Alta'),
    ]
    
    project_ids = []
    for p in projects_sample:
        project_ids.append(add_project(*p))
    
    # Alocações de exemplo
    allocations_sample = [
        (project_ids[0], 1, '2026-01-15', '2026-06-30', 480, 320, 'Lead Developer', 'Desenvolvimento principal'),
        (project_ids[0], 2, '2026-01-15', '2026-03-15', 240, 180, 'UX Designer', 'Design de interfaces'),
        (project_ids[0], 4, '2026-02-01', '2026-06-30', 400, 250, 'Backend Developer', 'APIs e integrações'),
        (project_ids[0], 5, '2026-04-01', '2026-06-30', 200, 80, 'QA', 'Testes e qualidade'),
        (project_ids[1], 1, '2026-02-01', '2026-08-31', 320, 0, 'Tech Lead', 'Liderança técnica'),
        (project_ids[1], 2, '2026-02-01', '2026-04-30', 280, 0, 'Designer', 'Design mobile'),
        (project_ids[2], 6, '2025-11-01', '2026-04-30', 600, 450, 'DevOps Lead', 'Migração AWS'),
        (project_ids[2], 4, '2025-11-01', '2026-04-30', 320, 240, 'Backend Dev', 'Adaptação de sistemas'),
    ]
    
    for a in allocations_sample:
        add_allocation(*a)
    
    return True


if __name__ == '__main__':
    init_database()
    if seed_sample_data():
        print("✓ Banco de dados inicializado com dados de exemplo")
    else:
        print("✓ Banco de dados já possui dados")
