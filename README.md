# 📊 ResourceHub - Gestão de Recursos de Projetos

Sistema desktop em Python para gestão completa de recursos em projetos. Solução **local**, **offline** e **gratuita**, ideal para equipes médias (10-50 pessoas).

## ✨ Funcionalidades

- ✅ **Cadastro de Projetos**: nome, cliente, gerente, orçamento, datas, status, prioridade
- ✅ **Cadastro de Recursos**: pessoas, equipamentos, taxa horária, capacidade, habilidades
- ✅ **Alocações**: vincular recursos a projetos com horas planejadas vs realizadas
- ✅ **Dashboard**: KPIs, gráficos de pizza e barras, utilização de recursos
- ✅ **Timeline (Gantt)**: visualização temporal das alocações por projeto ou recurso
- ✅ **Relatórios Excel**: 6 tipos diferentes de relatórios exportáveis
- ✅ **Banco SQLite local**: dados persistentes, sem necessidade de servidor

## 🚀 Instalação

### Pré-requisitos
- Python 3.8 ou superior
- Tkinter (geralmente já vem com Python)

### Passos

1. **Clone ou copie a pasta** `resource_manager` para o seu computador

2. **Instale as dependências**:
```bash
cd resource_manager
pip install -r requirements.txt
```

3. **Execute a aplicação**:
```bash
python app.py
```

## 📁 Estrutura do Projeto

```
resource_manager/
├── app.py                  # Aplicação principal e interface
├── database.py             # Gerenciamento do SQLite e queries
├── requirements.txt        # Dependências
├── README.md              # Esta documentação
├── data/                  # Banco de dados (criado automaticamente)
│   └── projects.db
├── exports/               # Relatórios exportados
└── views/
    ├── __init__.py
    ├── dashboard_view.py   # Dashboard com KPIs
    ├── projects_view.py    # CRUD de projetos
    ├── resources_view.py   # CRUD de recursos
    ├── allocations_view.py # CRUD de alocações
    ├── timeline_view.py    # Timeline/Gantt
    └── reports_view.py     # Geração de relatórios
```

## 💡 Como Usar

### Primeira Execução
Na primeira vez que abrir, o sistema oferecerá carregar **dados de exemplo** com projetos, recursos e alocações para você explorar.

### Fluxo Recomendado

1. **Cadastre Recursos** → Aba "Recursos" → "Novo Recurso"
   - Preencha nome, função, taxa horária, capacidade semanal

2. **Cadastre Projetos** → Aba "Projetos" → "Novo Projeto"
   - Preencha nome, cliente, datas, orçamento, status

3. **Crie Alocações** → Aba "Alocações" → "Nova Alocação"
   - Vincule recurso a projeto, defina horas planejadas
   - Atualize horas realizadas conforme avança o trabalho

4. **Visualize**:
   - **Dashboard** → KPIs gerais
   - **Timeline** → Gráfico Gantt visual
   - **Relatórios** → Exporte para Excel

## 📊 Tipos de Relatórios

| Relatório | Descrição |
|-----------|-----------|
| **Projetos** | Lista completa com todos os campos |
| **Recursos** | Cadastro de recursos com habilidades |
| **Alocações** | Plan vs Actual com variações |
| **Consolidado** | 4 abas: resumo, projetos, recursos, alocações |
| **Utilização** | Análise de capacidade e eficiência |
| **Custos** | Custo planejado vs realizado por projeto |

## 🎨 Tecnologias

- **Python 3.8+**: linguagem base
- **Tkinter**: interface gráfica nativa
- **SQLite**: banco de dados embarcado
- **Matplotlib**: gráficos e visualizações
- **OpenPyXL**: exportação para Excel

## 🔒 Privacidade

Todos os dados ficam **localmente** no arquivo `data/projects.db`. Nada é enviado para a internet.

## 🛠️ Próximas Evoluções (Roadmap)

- [ ] Autenticação multiusuário
- [ ] Backup/restauração automática
- [ ] Notificações de prazos
- [ ] Importação de dados via CSV/Excel
- [ ] API REST para integração
- [ ] Versão web (Flask/FastAPI)
- [ ] Sincronização em nuvem opcional

## 📝 Licença

Uso interno e livre. Adapte conforme necessário.

---

**Versão 1.0.0** - Desenvolvido como solução inicial local para gestão de recursos.
