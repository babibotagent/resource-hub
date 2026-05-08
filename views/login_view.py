"""
Login screen and change-password dialog.

The LoginView renders its UI *directly into the provided window* (no
Toplevel) — this avoids Windows visibility issues where a Toplevel of a
withdrawn root never gets a taskbar entry. The caller passes the Tk root,
LoginView fills it with the login card, and on success it clears the root
so the caller can build the main app UI on top of the same window.

The ChangePasswordDialog is still a modal Toplevel because it overlays an
already-visible main window (or the login window after sign-in).
"""

from __future__ import annotations

import logging
import os
import tkinter as tk
from tkinter import ttk

import auth
import i18n


ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          '..', 'assets')
LOGO_PATH = os.path.normpath(os.path.join(ASSETS_DIR, 'logo_128.png'))


# ===========================================================================
# Login view (built into the provided root window)
# ===========================================================================
class LoginView:
    """Login UI rendered directly into the provided root window.

    Usage:
        user = LoginView.run(root, colors)
        # `root` is now empty again on return (success or cancel).
    """

    @classmethod
    def run(cls, root, colors):
        v = cls(root, colors)
        # Wait until _finish() is called (sets _done=True) or the window
        # is destroyed (user closed the X).
        v._wait_var = tk.IntVar(master=root, value=0)
        root.wait_variable(v._wait_var)
        # Tear down login UI but keep the root alive
        for child in list(root.winfo_children()):
            try: child.destroy()
            except Exception: pass
        # Drop our language listener so we don't re-render dead widgets
        try: i18n.remove_listener(v._on_language_change)
        except Exception: pass
        return v.user

    def __init__(self, root, colors):
        self.root = root
        self.colors = colors
        self.user = None
        self._wait_var = None
        self._logo = None

        # Reset the root so we own its content
        for child in list(root.winfo_children()):
            try: child.destroy()
            except Exception: pass

        self.root.title(i18n.t('login.title'))
        self.root.configure(bg=colors['background'])
        # Re-center if needed
        try: self.root.geometry('480x560')
        except Exception: pass
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)

        i18n.add_listener(self._on_language_change)
        self._build()
        # Force focus to the username field
        self.root.lift()
        self.root.focus_force()

    # ---------------------------------------------------------------------
    def _build(self):
        # Card centered in the root
        card = tk.Frame(self.root, bg=self.colors['surface'],
                        highlightbackground=self.colors['border'],
                        highlightthickness=1)
        card.place(relx=0.5, rely=0.5, anchor='center', width=420, height=500)

        # Language toggle (top-right of card)
        lang_box = tk.Frame(card, bg=self.colors['surface'])
        lang_box.pack(anchor='ne', padx=12, pady=8)
        self._lang_buttons = {}
        for code in ('en', 'fr'):
            b = tk.Button(lang_box, text=code.upper(),
                          font=('Segoe UI', 9, 'bold'),
                          bd=0, padx=8, pady=2, cursor='hand2',
                          command=lambda c=code: self._switch_lang(c))
            b.pack(side='left', padx=2)
            self._lang_buttons[code] = b
        self._refresh_lang_buttons()

        # Logo
        try:
            self._logo = tk.PhotoImage(file=LOGO_PATH)
            tk.Label(card, image=self._logo,
                     bg=self.colors['surface']).pack(pady=(8, 8))
        except Exception:
            tk.Label(card, text='[RH]', font=('Segoe UI', 28, 'bold'),
                     bg=self.colors['surface'],
                     fg=self.colors['primary']).pack(pady=(8, 8))

        self._title_label = tk.Label(card, text=i18n.t('login.title'),
                                     font=('Segoe UI', 16, 'bold'),
                                     bg=self.colors['surface'],
                                     fg=self.colors['text'])
        self._title_label.pack(pady=(0, 18))

        form = tk.Frame(card, bg=self.colors['surface'])
        form.pack(padx=32, fill='x')

        self._user_label = tk.Label(form, text=i18n.t('login.username'),
                                    font=('Segoe UI', 9),
                                    bg=self.colors['surface'],
                                    fg=self.colors['text_light'])
        self._user_label.pack(anchor='w')
        self.username_var = tk.StringVar()
        self.username_entry = tk.Entry(form, textvariable=self.username_var,
                                       font=('Segoe UI', 11),
                                       bd=1, relief='solid')
        self.username_entry.pack(fill='x', ipady=6, pady=(2, 12))

        self._pwd_label = tk.Label(form, text=i18n.t('login.password'),
                                   font=('Segoe UI', 9),
                                   bg=self.colors['surface'],
                                   fg=self.colors['text_light'])
        self._pwd_label.pack(anchor='w')
        self.password_var = tk.StringVar()
        self.password_entry = tk.Entry(form, textvariable=self.password_var,
                                       font=('Segoe UI', 11),
                                       bd=1, relief='solid', show='*')
        self.password_entry.pack(fill='x', ipady=6, pady=(2, 12))
        self.password_entry.bind('<Return>', lambda e: self._submit())
        self.username_entry.bind('<Return>',
                                 lambda e: self.password_entry.focus())

        self.error_label = tk.Label(form, text='', font=('Segoe UI', 9),
                                    bg=self.colors['surface'],
                                    fg=self.colors['danger'], wraplength=340,
                                    justify='left')
        self.error_label.pack(anchor='w', pady=(4, 0))

        self._login_btn = tk.Button(form, text=i18n.t('btn.login'),
                                    font=('Segoe UI', 11, 'bold'),
                                    bg=self.colors['primary'], fg='white',
                                    activebackground=self.colors['primary_dark'],
                                    activeforeground='white',
                                    bd=0, padx=20, pady=10, cursor='hand2',
                                    command=self._submit)
        self._login_btn.pack(fill='x', pady=(18, 0))

        self._hint_label = tk.Label(card, text=i18n.t('login.first_run_hint'),
                                    font=('Segoe UI', 8),
                                    bg=self.colors['surface'],
                                    fg=self.colors['text_light'])
        self._hint_label.pack(side='bottom', pady=12)

        self.username_entry.focus_set()

    def _switch_lang(self, code):
        i18n.set_language(code)

    def _refresh_lang_buttons(self):
        active = i18n.get_language()
        for code, btn in self._lang_buttons.items():
            if code == active:
                btn.configure(bg=self.colors['primary'], fg='white')
            else:
                btn.configure(bg=self.colors['border'],
                              fg=self.colors['text_light'])

    def _on_language_change(self, _new_lang):
        try:
            self.root.title(i18n.t('login.title'))
            self._title_label.configure(text=i18n.t('login.title'))
            self._user_label.configure(text=i18n.t('login.username'))
            self._pwd_label.configure(text=i18n.t('login.password'))
            self._login_btn.configure(text=i18n.t('btn.login'))
            self._hint_label.configure(text=i18n.t('login.first_run_hint'))
            self._refresh_lang_buttons()
        except tk.TclError:
            pass  # widgets already destroyed

    def _submit(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        try:
            user = auth.login(username, password)
        except auth.LoginError as exc:
            logging.warning(f"Login failed: {exc.code}")
            self._show_error(exc.code)
            self.password_var.set('')
            self.password_entry.focus()
            return
        self.user = user
        self._finish()

    def _show_error(self, code):
        mapping = {
            'empty_credentials': 'login.error.empty_credentials',
            'unknown_user':      'login.error.unknown',
            'bad_password':      'login.error.bad_pass',
            'inactive_user':     'login.error.inactive',
        }
        key = mapping.get(code, 'login.error.bad_pass')
        self.error_label.configure(text=i18n.t(key))

    def _on_close(self):
        # User clicked the window's X — signal cancel
        self.user = None
        self._finish()

    def _finish(self):
        if self._wait_var is not None:
            try:
                self._wait_var.set(1)
            except Exception:
                pass


# ===========================================================================
# Change password dialog (still a Toplevel, overlays the visible window)
# ===========================================================================
class ChangePasswordDialog:
    """Modal dialog for changing the current user's password.

    ``force=True`` removes the cancel button and disables the close button.
    Returns ``True`` on success, ``False`` if cancelled.
    """

    @classmethod
    def run(cls, root, colors, user, force=False):
        d = cls(root, colors, user, force)
        root.wait_window(d.window)
        return d.success

    def __init__(self, root, colors, user, force):
        self.root = root
        self.colors = colors
        self.user = user
        self.force = force
        self.success = False

        i18n.add_listener(self._on_language_change)
        self._build()

    def _build(self):
        self.window = tk.Toplevel(self.root)
        self.window.configure(bg=self.colors['surface'])
        self.window.title(i18n.t('pwd.change.title'))
        self.window.geometry('420x460')
        self.window.resizable(False, False)
        try:
            self.window.transient(self.root)
        except Exception:
            pass
        self.window.grab_set()
        self.window.lift()
        self.window.focus_force()
        self.window.attributes('-topmost', True)
        self.window.after(200, lambda: self.window.attributes('-topmost', False))
        if self.force:
            self.window.protocol('WM_DELETE_WINDOW', lambda: None)
        else:
            self.window.protocol('WM_DELETE_WINDOW', self._on_cancel)
        self.window.update_idletasks()
        sw, sh = self.window.winfo_screenwidth(), self.window.winfo_screenheight()
        self.window.geometry(f"420x460+{(sw-420)//2}+{(sh-460)//2}")

        body = tk.Frame(self.window, bg=self.colors['surface'])
        body.pack(fill='both', expand=True, padx=28, pady=24)

        self._title_label = tk.Label(body, text=i18n.t('pwd.change.title'),
                                     font=('Segoe UI', 14, 'bold'),
                                     bg=self.colors['surface'],
                                     fg=self.colors['text'])
        self._title_label.pack(anchor='w')

        if self.force:
            self._notice_label = tk.Label(body,
                text=i18n.t('pwd.change.required'),
                font=('Segoe UI', 9), wraplength=360, justify='left',
                bg=self.colors['surface'], fg=self.colors['warning'])
            self._notice_label.pack(anchor='w', pady=(6, 16))
        else:
            self._notice_label = None

        self._cur_label = self._labeled_entry(body, 'pwd.change.current')
        self.current_var = tk.StringVar()
        self._cur_entry = tk.Entry(body, textvariable=self.current_var,
                                   font=('Segoe UI', 11), bd=1, relief='solid',
                                   show='*')
        self._cur_entry.pack(fill='x', ipady=6, pady=(2, 10))

        self._new_label = self._labeled_entry(body, 'pwd.change.new')
        self.new_var = tk.StringVar()
        self._new_entry = tk.Entry(body, textvariable=self.new_var,
                                   font=('Segoe UI', 11), bd=1, relief='solid',
                                   show='*')
        self._new_entry.pack(fill='x', ipady=6, pady=(2, 10))

        self._confirm_label = self._labeled_entry(body, 'pwd.change.confirm')
        self.confirm_var = tk.StringVar()
        self._confirm_entry = tk.Entry(body, textvariable=self.confirm_var,
                                       font=('Segoe UI', 11), bd=1, relief='solid',
                                       show='*')
        self._confirm_entry.pack(fill='x', ipady=6, pady=(2, 10))

        self.error_label = tk.Label(body, text='', font=('Segoe UI', 9),
                                    bg=self.colors['surface'],
                                    fg=self.colors['danger'], wraplength=360,
                                    justify='left')
        self.error_label.pack(anchor='w', pady=(4, 0))

        btn_row = tk.Frame(body, bg=self.colors['surface'])
        btn_row.pack(fill='x', pady=(20, 0))
        self._save_btn = tk.Button(btn_row, text=i18n.t('btn.save'),
                                   font=('Segoe UI', 10, 'bold'),
                                   bg=self.colors['primary'], fg='white',
                                   activebackground=self.colors['primary_dark'],
                                   bd=0, padx=14, pady=8, cursor='hand2',
                                   command=self._submit)
        self._save_btn.pack(side='right', padx=(8, 0))
        if not self.force:
            self._cancel_btn = tk.Button(btn_row, text=i18n.t('btn.cancel'),
                                         font=('Segoe UI', 10),
                                         bg=self.colors['border'], bd=0,
                                         padx=14, pady=8, cursor='hand2',
                                         command=self._on_cancel)
            self._cancel_btn.pack(side='right')

        self._cur_entry.focus_set()
        self._confirm_entry.bind('<Return>', lambda e: self._submit())

    def _labeled_entry(self, parent, key):
        lbl = tk.Label(parent, text=i18n.t(key), font=('Segoe UI', 9),
                       bg=self.colors['surface'],
                       fg=self.colors['text_light'])
        lbl.pack(anchor='w', pady=(4, 0))
        return lbl

    def _submit(self):
        current = self.current_var.get()
        new = self.new_var.get()
        confirm = self.confirm_var.get()

        if not new or len(new) < 4:
            self.error_label.configure(text=i18n.t('pwd.change.error.short'))
            return
        if new != confirm:
            self.error_label.configure(text=i18n.t('pwd.change.error.match'))
            return

        try:
            auth.login(self.user['username'], current)
        except auth.LoginError:
            self.error_label.configure(text=i18n.t('pwd.change.error.current'))
            return

        try:
            auth.set_password(self.user['user_id'], new, clear_must_change=True)
        except ValueError as e:
            self.error_label.configure(text=str(e))
            return

        self.success = True
        try: i18n.remove_listener(self._on_language_change)
        except Exception: pass
        self.window.destroy()

    def _on_cancel(self):
        if self.force:
            return
        try: i18n.remove_listener(self._on_language_change)
        except Exception: pass
        self.window.destroy()

    def _on_language_change(self, _new_lang):
        try:
            self.window.title(i18n.t('pwd.change.title'))
            self._title_label.configure(text=i18n.t('pwd.change.title'))
            if self._notice_label is not None:
                self._notice_label.configure(text=i18n.t('pwd.change.required'))
            self._cur_label.configure(text=i18n.t('pwd.change.current'))
            self._new_label.configure(text=i18n.t('pwd.change.new'))
            self._confirm_label.configure(text=i18n.t('pwd.change.confirm'))
            self._save_btn.configure(text=i18n.t('btn.save'))
            if not self.force:
                self._cancel_btn.configure(text=i18n.t('btn.cancel'))
        except tk.TclError:
            pass
