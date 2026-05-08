"""
i18n module for ResourceHub.

Two languages: English (en) and French (fr). English is the default.

Usage
-----
    import i18n
    i18n.set_language('fr')
    label = i18n.t('nav.dashboard')        # 'Tableau de bord'
    label = i18n.t('app.title', lang='en') # forced English

Adding a key
------------
Always add it to BOTH 'en' and 'fr'. If a key is missing in a language,
``t`` falls back to English; if it's missing there too, it returns the key
itself wrapped in '??' so the gap is visible in the UI.
"""

from __future__ import annotations

DEFAULT_LANGUAGE = 'en'
SUPPORTED_LANGUAGES = ('en', 'fr')

_current_language = DEFAULT_LANGUAGE
_listeners: list = []


TRANSLATIONS = {
    'en': {
        # -------------------- App chrome --------------------
        'app.title':            'ResourceHub - Project Management',
        'app.tagline':          'Plan. Track. Deliver.',
        'app.version':          'v2.1.0',
        'app.language':         'Language',
        'app.language.en':      'English',
        'app.language.fr':      'French',

        # -------------------- Navigation --------------------
        'nav.dashboard':        'Dashboard',
        'nav.projects':         'Projects',
        'nav.tasks':            'Tasks',
        'nav.employees':        'Employees',
        'nav.externals':        'External resources',
        'nav.customers':        'Customers',
        'nav.assignments':      'Assignments',
        'nav.knowledge':        'Skills',
        'nav.timeentries':      'Time entries',
        'nav.risks':            'Risks',
        'nav.invoices':         'Invoices',
        'nav.departments':      'Departments',
        'nav.reports':          'Reports',
        'nav.users':            'Users',

        # -------------------- Buttons --------------------
        'btn.new':              'New',
        'btn.edit':             'Edit',
        'btn.delete':           'Delete',
        'btn.save':             'Save',
        'btn.cancel':           'Cancel',
        'btn.refresh':          'Refresh',
        'btn.export':           'Export',
        'btn.import':           'Import',
        'btn.search':           'Search',
        'btn.close':            'Close',
        'btn.login':            'Sign in',
        'btn.logout':           'Sign out',
        'btn.add':              'Add',
        'btn.remove':           'Remove',
        'btn.reset_password':   'Reset password',

        # -------------------- Generic --------------------
        'common.coming_soon':   'Coming soon',
        'common.coming_soon.desc':
            'This screen has not been migrated to the new schema yet. '
            'It will be added in a future iteration.',
        'common.empty':         'No data to show.',
        'common.loading':       'Loading...',
        'common.yes':           'Yes',
        'common.no':            'No',
        'common.total':         'Total',
        'common.error':         'Error',
        'common.warning':       'Warning',
        'common.info':          'Info',
        'common.confirm':       'Confirm',
        'common.confirm_delete': 'Are you sure you want to delete this?',

        # -------------------- Login --------------------
        'login.title':              'Sign in to ResourceHub',
        'login.username':           'Username',
        'login.password':           'Password',
        'login.error.empty':        'Please enter username and password.',
        'login.error.unknown':      'Unknown user.',
        'login.error.bad_pass':     'Incorrect password.',
        'login.error.inactive':     'This account is disabled.',
        'login.error.empty_credentials': 'Please enter username and password.',
        'login.welcome':            'Welcome,',
        'login.first_run_hint':     'First time? Default credentials are admin / admin.',

        # -------------------- Change password --------------------
        'pwd.change.title':         'Change password',
        'pwd.change.required':      'You must change your password before continuing.',
        'pwd.change.current':       'Current password',
        'pwd.change.new':           'New password',
        'pwd.change.confirm':       'Confirm new password',
        'pwd.change.error.short':   'Password must be at least 4 characters.',
        'pwd.change.error.match':   'New passwords do not match.',
        'pwd.change.error.current': 'Current password is incorrect.',
        'pwd.change.success':       'Password changed.',

        # -------------------- Users management --------------------
        'users.title':              'Users management',
        'users.subtitle':           'Create users, set their role and grant project access.',
        'users.col.username':       'Username',
        'users.col.role':           'Role',
        'users.col.employee':       'Linked employee',
        'users.col.active':         'Active',
        'users.col.last_login':     'Last login',
        'users.dialog.new':         'New user',
        'users.dialog.edit':        'Edit user',
        'users.field.username':     'Username',
        'users.field.password':     'Password',
        'users.field.role':         'Role',
        'users.field.employee':     'Linked employee (optional)',
        'users.field.active':       'Active',
        'users.field.must_change':  'Force password change at next login',
        'users.access.title':       'Project access',
        'users.access.col.project': 'Project',
        'users.access.col.role':    'Project role',
        'users.access.col.granted': 'Granted',
        'users.access.empty':       'No project access granted yet.',
        'users.access.add':         'Grant access',
        'users.confirm.delete':     'Delete this user? This cannot be undone.',

        # -------------------- Roles --------------------
        'role.admin':               'Administrator',
        'role.project_manager':     'Project manager',
        'role.member':              'Member',
        'role.viewer':              'Viewer',

        # -------------------- Permission denied --------------------
        'perm.denied':              'You do not have permission to access this section.',
        'perm.denied.action':       'You do not have permission for this action.',

        # -------------------- Dashboard --------------------
        'dash.title':                   'Dashboard',
        'dash.subtitle':                'Overview of your projects, people and finances',
        'dash.kpi.employees':           'Employees',
        'dash.kpi.externals':           'External resources',
        'dash.kpi.customers':           'Customers',
        'dash.kpi.projects':            'Projects',
        'dash.kpi.active_projects':     'Active projects',
        'dash.kpi.tasks':                'Tasks',
        'dash.kpi.open_tasks':           'Open tasks',
        'dash.kpi.invoices':             'Invoices',
        'dash.kpi.outstanding_amount':   'Outstanding amount',
        'dash.kpi.total_budget':         'Total budget',
        'dash.kpi.actual_cost':          'Actual cost',
        'dash.kpi.budget_used_pct':      'Budget used',
        'dash.section.projects_status':  'Projects by status',
        'dash.section.top_budget':       'Top projects by % spent',
        'dash.section.recent_risks':     'Recent risks',
        'dash.section.invoices_status':  'Invoices by status',

        # -------------------- Project statuses --------------------
        'status.planning':      'Planning',
        'status.in_progress':   'In progress',
        'status.on_hold':       'On hold',
        'status.completed':     'Completed',
        'status.cancelled':     'Cancelled',

        # -------------------- Task statuses --------------------
        'task.todo':            'To do',
        'task.in_progress':     'In progress',
        'task.in_review':       'In review',
        'task.done':            'Done',
        'task.blocked':         'Blocked',

        # -------------------- Priority --------------------
        'priority.low':         'Low',
        'priority.medium':      'Medium',
        'priority.high':        'High',
        'priority.critical':    'Critical',

        # -------------------- Invoice statuses --------------------
        'invoice.draft':        'Draft',
        'invoice.sent':         'Sent',
        'invoice.paid':         'Paid',
        'invoice.overdue':      'Overdue',
        'invoice.cancelled':    'Cancelled',

        # -------------------- Risk --------------------
        'risk.identified':      'Identified',
        'risk.mitigating':      'Mitigating',
        'risk.resolved':        'Resolved',
        'risk.accepted':        'Accepted',

        # -------------------- First run --------------------
        'firstrun.title':       'Welcome',
        'firstrun.message':     ('No data found. Would you like to load the sample '
                                 'dataset (Portuguese projects, employees and customers) '
                                 'so you can explore the app?'),
        'firstrun.loaded':      'Sample data loaded.',
    },

    'fr': {
        # -------------------- App chrome --------------------
        'app.title':            'ResourceHub - Gestion de projets',
        'app.tagline':          'Planifier. Suivre. Livrer.',
        'app.version':          'v2.1.0',
        'app.language':         'Langue',
        'app.language.en':      'Anglais',
        'app.language.fr':      'Francais',

        # -------------------- Navigation --------------------
        'nav.dashboard':        'Tableau de bord',
        'nav.projects':         'Projets',
        'nav.tasks':            'Taches',
        'nav.employees':        'Employes',
        'nav.externals':        'Ressources externes',
        'nav.customers':        'Clients',
        'nav.assignments':      'Affectations',
        'nav.knowledge':        'Competences',
        'nav.timeentries':      'Saisie de temps',
        'nav.risks':            'Risques',
        'nav.invoices':         'Factures',
        'nav.departments':      'Departements',
        'nav.reports':          'Rapports',
        'nav.users':            'Utilisateurs',

        # -------------------- Buttons --------------------
        'btn.new':              'Nouveau',
        'btn.edit':             'Modifier',
        'btn.delete':           'Supprimer',
        'btn.save':             'Enregistrer',
        'btn.cancel':           'Annuler',
        'btn.refresh':          'Actualiser',
        'btn.export':           'Exporter',
        'btn.import':           'Importer',
        'btn.search':           'Rechercher',
        'btn.close':            'Fermer',
        'btn.login':            'Se connecter',
        'btn.logout':           'Se deconnecter',
        'btn.add':              'Ajouter',
        'btn.remove':           'Retirer',
        'btn.reset_password':   'Reinitialiser le mot de passe',

        # -------------------- Generic --------------------
        'common.coming_soon':   'Bientot disponible',
        'common.coming_soon.desc':
            "Cet ecran n'a pas encore ete migre vers le nouveau schema. "
            "Il sera ajoute dans une prochaine iteration.",
        'common.empty':         'Aucune donnee a afficher.',
        'common.loading':       'Chargement...',
        'common.yes':           'Oui',
        'common.no':            'Non',
        'common.total':         'Total',
        'common.error':         'Erreur',
        'common.warning':       'Avertissement',
        'common.info':          'Information',
        'common.confirm':       'Confirmer',
        'common.confirm_delete': 'Etes-vous sur de vouloir supprimer ?',

        # -------------------- Login --------------------
        'login.title':              'Connexion a ResourceHub',
        'login.username':           "Nom d'utilisateur",
        'login.password':           'Mot de passe',
        'login.error.empty':        "Veuillez saisir nom d'utilisateur et mot de passe.",
        'login.error.unknown':      "Utilisateur inconnu.",
        'login.error.bad_pass':     'Mot de passe incorrect.',
        'login.error.inactive':     'Ce compte est desactive.',
        'login.error.empty_credentials': "Veuillez saisir nom d'utilisateur et mot de passe.",
        'login.welcome':            'Bienvenue,',
        'login.first_run_hint':     'Premiere fois ? Identifiants par defaut : admin / admin.',

        # -------------------- Change password --------------------
        'pwd.change.title':         'Changer le mot de passe',
        'pwd.change.required':      'Vous devez changer votre mot de passe avant de continuer.',
        'pwd.change.current':       'Mot de passe actuel',
        'pwd.change.new':           'Nouveau mot de passe',
        'pwd.change.confirm':       'Confirmer le nouveau mot de passe',
        'pwd.change.error.short':   'Le mot de passe doit faire au moins 4 caracteres.',
        'pwd.change.error.match':   'Les nouveaux mots de passe ne correspondent pas.',
        'pwd.change.error.current': 'Le mot de passe actuel est incorrect.',
        'pwd.change.success':       'Mot de passe change.',

        # -------------------- Users management --------------------
        'users.title':              'Gestion des utilisateurs',
        'users.subtitle':           'Creer des utilisateurs, definir leur role et donner acces aux projets.',
        'users.col.username':       "Nom d'utilisateur",
        'users.col.role':           'Role',
        'users.col.employee':       'Employe lie',
        'users.col.active':         'Actif',
        'users.col.last_login':     'Derniere connexion',
        'users.dialog.new':         'Nouvel utilisateur',
        'users.dialog.edit':        "Modifier l'utilisateur",
        'users.field.username':     "Nom d'utilisateur",
        'users.field.password':     'Mot de passe',
        'users.field.role':         'Role',
        'users.field.employee':     'Employe lie (optionnel)',
        'users.field.active':       'Actif',
        'users.field.must_change':  'Forcer le changement de mot de passe a la prochaine connexion',
        'users.access.title':       'Acces aux projets',
        'users.access.col.project': 'Projet',
        'users.access.col.role':    'Role projet',
        'users.access.col.granted': 'Accorde le',
        'users.access.empty':       'Aucun acces projet accorde.',
        'users.access.add':         "Donner l'acces",
        'users.confirm.delete':     'Supprimer cet utilisateur ? Cette action est definitive.',

        # -------------------- Roles --------------------
        'role.admin':               'Administrateur',
        'role.project_manager':     'Chef de projet',
        'role.member':              'Membre',
        'role.viewer':              'Lecteur',

        # -------------------- Permission denied --------------------
        'perm.denied':              "Vous n'avez pas la permission d'acceder a cette section.",
        'perm.denied.action':       "Vous n'avez pas la permission pour cette action.",

        # -------------------- Dashboard --------------------
        'dash.title':                   'Tableau de bord',
        'dash.subtitle':                "Vue d'ensemble de vos projets, equipes et finances",
        'dash.kpi.employees':           'Employes',
        'dash.kpi.externals':           'Ressources externes',
        'dash.kpi.customers':           'Clients',
        'dash.kpi.projects':            'Projets',
        'dash.kpi.active_projects':     'Projets actifs',
        'dash.kpi.tasks':                'Taches',
        'dash.kpi.open_tasks':           'Taches ouvertes',
        'dash.kpi.invoices':             'Factures',
        'dash.kpi.outstanding_amount':   'Montant en attente',
        'dash.kpi.total_budget':         'Budget total',
        'dash.kpi.actual_cost':          'Cout reel',
        'dash.kpi.budget_used_pct':      'Budget consomme',
        'dash.section.projects_status':  'Projets par statut',
        'dash.section.top_budget':       'Top projets par % consomme',
        'dash.section.recent_risks':     'Risques recents',
        'dash.section.invoices_status':  'Factures par statut',

        # -------------------- Project statuses --------------------
        'status.planning':      'Planification',
        'status.in_progress':   'En cours',
        'status.on_hold':       'En attente',
        'status.completed':     'Termine',
        'status.cancelled':     'Annule',

        # -------------------- Task statuses --------------------
        'task.todo':            'A faire',
        'task.in_progress':     'En cours',
        'task.in_review':       'En revue',
        'task.done':            'Terminee',
        'task.blocked':         'Bloquee',

        # -------------------- Priority --------------------
        'priority.low':         'Basse',
        'priority.medium':      'Moyenne',
        'priority.high':        'Haute',
        'priority.critical':    'Critique',

        # -------------------- Invoice statuses --------------------
        'invoice.draft':        'Brouillon',
        'invoice.sent':         'Envoyee',
        'invoice.paid':         'Payee',
        'invoice.overdue':      'En retard',
        'invoice.cancelled':    'Annulee',

        # -------------------- Risk --------------------
        'risk.identified':      'Identifie',
        'risk.mitigating':      'En mitigation',
        'risk.resolved':        'Resolu',
        'risk.accepted':        'Accepte',

        # -------------------- First run --------------------
        'firstrun.title':       'Bienvenue',
        'firstrun.message':     ('Aucune donnee trouvee. Souhaitez-vous charger le jeu '
                                 "de donnees d'exemple (projets, employes et clients "
                                 "portugais) pour explorer l'application ?"),
        'firstrun.loaded':      "Donnees d'exemple chargees.",
    },
}


def set_language(lang):
    global _current_language
    if lang not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {lang!r}. Use one of {SUPPORTED_LANGUAGES}.")
    if lang == _current_language:
        return
    _current_language = lang
    for cb in list(_listeners):
        try:
            cb(lang)
        except Exception:
            pass


def get_language():
    return _current_language


def add_listener(callback):
    if callback not in _listeners:
        _listeners.append(callback)


def remove_listener(callback):
    if callback in _listeners:
        _listeners.remove(callback)


def t(key, lang=None):
    use_lang = lang or _current_language
    table = TRANSLATIONS.get(use_lang, {})
    if key in table:
        return table[key]
    fallback = TRANSLATIONS.get(DEFAULT_LANGUAGE, {})
    if key in fallback:
        return fallback[key]
    return f"??{key}??"


def t_status(value):
    return '' if not value else t(f"status.{value}")


def t_task_status(value):
    return '' if not value else t(f"task.{value}")


def t_priority(value):
    return '' if not value else t(f"priority.{value}")


def t_invoice_status(value):
    return '' if not value else t(f"invoice.{value}")


def t_risk_status(value):
    return '' if not value else t(f"risk.{value}")


def t_role(value):
    return '' if not value else t(f"role.{value}")
