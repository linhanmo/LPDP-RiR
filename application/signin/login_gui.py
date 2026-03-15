import tkinter as tk
from tkinter import ttk, messagebox
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
APPLICATION_DIR = CURRENT_DIR.parent
APP_ROOT = APPLICATION_DIR.parent

if str(APPLICATION_DIR) not in sys.path:
    sys.path.append(str(APPLICATION_DIR))
if str(APP_ROOT) not in sys.path:
    sys.path.append(str(APP_ROOT))

try:
    from application.data.dataloader import (
        authenticate_user,
        set_current_user,
        get_user_by_username,
    )
    from application.signin.register_gui import RegisterWindow
    from application.signin.changepassword_gui import ChangePasswordWindow
except ImportError:
    try:
        from data.dataloader import (
            authenticate_user,
            set_current_user,
            get_user_by_username,
        )
        from signin.register_gui import RegisterWindow
        from signin.changepassword_gui import ChangePasswordWindow
    except ImportError:
        from dataloader import authenticate_user, set_current_user, get_user_by_username
        from register_gui import RegisterWindow
        from changepassword_gui import ChangePasswordWindow

try:
    from application.data.dataloader import authenticate_user, set_current_user
except ImportError:
    from data.dataloader import authenticate_user, set_current_user

try:
    from .register_gui import RegisterWindow
    from .changepassword_gui import ChangePasswordWindow
except ImportError:
    from register_gui import RegisterWindow
    from changepassword_gui import ChangePasswordWindow

from application.gui import styles, languages

try:
    from application.data.config_manager import (
        set_language,
        save_credentials,
        get_credentials,
        get_theme_index,
        set_theme_index,
    )
except ImportError:
    try:
        from data.config_manager import (
            set_language,
            save_credentials,
            get_credentials,
            get_theme_index,
            set_theme_index,
        )
    except ImportError:

        def set_language(lang):
            pass

        def save_credentials(u, p, r):
            pass

        def get_credentials():
            return "", ""

        def get_theme_index():
            return 0

        def set_theme_index(index):
            pass


class LoginApp(tk.Tk):
    def __init__(self, language="CN"):
        super().__init__()
        self.current_language = language
        self.title(languages.get_text("login_title", self.current_language))
        self.geometry("500x400")
        self.resizable(False, False)
        self.login_success = False

        try:
            icon_path = CURRENT_DIR.parent / "logo" / "logo.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception:
            pass

        self.center_window()
        self.create_widgets()
        self.apply_theme()
        self.load_saved_credentials()

    def load_saved_credentials(self):
        saved_username, saved_password = get_credentials()
        if saved_username:
            self.username_var.set(saved_username)
            self.password_var.set(saved_password)
            self.remember_var.set(True)

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="30")
        main_frame.pack(fill=tk.BOTH, expand=True)

        top_btn_frame = tk.Frame(self)
        top_btn_frame.place(relx=1.0, y=10, x=-10, anchor="ne")

        self.lang_label = tk.Label(
            top_btn_frame,
            text=languages.get_text("label_language", self.current_language),
            font=styles.FONT_LABEL_BOLD_CN,
        )
        self.lang_label.pack(side=tk.LEFT, padx=(5, 2))

        self.lang_btn = tk.Button(
            top_btn_frame,
            text=languages.get_text("lang_switch", self.current_language),
            font=styles.FONT_BUTTON_CN,
            relief=tk.FLAT,
            bd=0,
            command=self.switch_language,
        )
        self.lang_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.theme_label = tk.Label(
            top_btn_frame,
            text=languages.get_text("label_theme", self.current_language),
            font=styles.FONT_LABEL_BOLD_CN,
        )
        self.theme_label.pack(side=tk.LEFT, padx=(5, 2))

        theme_names = [
            languages.get_text(key, self.current_language) for key in styles.THEME_KEYS
        ]
        self.theme_combo = ttk.Combobox(
            top_btn_frame,
            values=theme_names,
            state="readonly",
            font=styles.FONT_BUTTON_CN,
            width=25,
        )
        current_idx = get_theme_index()
        if 0 <= current_idx < len(theme_names):
            self.theme_combo.current(current_idx)
        else:
            self.theme_combo.current(0)

        self.theme_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.theme_combo.bind("<<ComboboxSelected>>", self.on_theme_selected)

        self.top_btn_frame = top_btn_frame

        self.title_label = ttk.Label(
            main_frame,
            text=languages.get_text("login_welcome", self.current_language),
            font=styles.FONT_SUBTITLE_CN,
        )
        self.title_label.pack(pady=(25, 20))

        user_frame = ttk.Frame(main_frame)
        user_frame.pack(fill=tk.X, pady=5)
        self.user_label = ttk.Label(
            user_frame,
            text=languages.get_text("label_username", self.current_language),
            width=10,
        )
        self.user_label.pack(side=tk.LEFT)
        self.username_var = tk.StringVar()
        self.username_entry = ttk.Entry(user_frame, textvariable=self.username_var)
        self.username_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        pass_frame = ttk.Frame(main_frame)
        pass_frame.pack(fill=tk.X, pady=5)
        self.pass_label = ttk.Label(
            pass_frame,
            text=languages.get_text("label_password", self.current_language),
            width=10,
        )
        self.pass_label.pack(side=tk.LEFT)
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(
            pass_frame, textvariable=self.password_var, show="*"
        )
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.password_entry.bind("<Return>", lambda e: self.on_login())

        self.remember_var = tk.BooleanVar()
        self.remember_check = ttk.Checkbutton(
            main_frame,
            text=languages.get_text("remember_me", self.current_language),
            variable=self.remember_var,
        )
        self.remember_check.pack(pady=(10, 0), anchor="w")

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=20)

        self.login_btn = ttk.Button(
            btn_frame,
            text=languages.get_text("btn_login", self.current_language),
            command=self.on_login,
        )
        self.login_btn.pack(fill=tk.X, pady=(0, 10))

        link_frame = ttk.Frame(main_frame)
        link_frame.pack(fill=tk.X)

        self.register_link = ttk.Label(
            link_frame,
            text=languages.get_text("link_register", self.current_language),
            foreground="blue",
            cursor="hand2",
        )
        self.register_link.pack(side=tk.LEFT)
        self.register_link.bind("<Button-1>", lambda e: self.open_register())

        self.forgot_link = ttk.Label(
            link_frame,
            text=languages.get_text("link_change_password", self.current_language),
            foreground="blue",
            cursor="hand2",
        )
        self.forgot_link.pack(side=tk.RIGHT)
        self.forgot_link.bind("<Button-1>", lambda e: self.open_change_password())

    def switch_language(self):
        self.current_language = "EN" if self.current_language == "CN" else "CN"
        set_language(self.current_language)
        self.update_language()

    def update_language(self):
        lang = self.current_language
        self.title(languages.get_text("login_title", lang))
        self.lang_btn.config(text=languages.get_text("lang_switch", lang))
        self.lang_label.config(text=languages.get_text("label_language", lang))
        self.theme_label.config(text=languages.get_text("label_theme", lang))

        current_idx = self.theme_combo.current()
        theme_names = [languages.get_text(key, lang) for key in styles.THEME_KEYS]
        self.theme_combo["values"] = theme_names
        if current_idx >= 0:
            self.theme_combo.current(current_idx)

        self.title_label.config(text=languages.get_text("login_welcome", lang))
        self.user_label.config(text=languages.get_text("label_username", lang))
        self.pass_label.config(text=languages.get_text("label_password", lang))
        self.remember_check.config(text=languages.get_text("remember_me", lang))
        self.login_btn.config(text=languages.get_text("btn_login", lang))
        self.register_link.config(text=languages.get_text("link_register", lang))
        self.forgot_link.config(text=languages.get_text("link_change_password", lang))

    def on_theme_selected(self, event):
        selected_index = self.theme_combo.current()
        if selected_index >= 0:
            set_theme_index(selected_index)
            self.apply_theme()

    def apply_theme(self):
        theme_index = get_theme_index()
        bg_color = styles.THEME_COLORS[theme_index]["hex"]
        self.configure(bg=bg_color)

        style = ttk.Style()
        style.configure(".", background=bg_color)
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color)
        style.configure("TButton", background=bg_color)
        style.configure("TCheckbutton", background=bg_color)
        style.configure("TEntry", fieldbackground="white")

        if hasattr(self, "top_btn_frame"):
            self.top_btn_frame.configure(bg=bg_color)
        if hasattr(self, "lang_label"):
            self.lang_label.configure(bg=bg_color)
        if hasattr(self, "theme_label"):
            self.theme_label.configure(bg=bg_color)
        if hasattr(self, "lang_btn"):
            self.lang_btn.configure(bg=bg_color, activebackground=bg_color)

    def on_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        lang = self.current_language

        if not username or not password:
            messagebox.showwarning(
                languages.get_text("title_warning", lang),
                languages.get_text("msg_enter_user_pass", lang),
            )
            return

        if get_user_by_username(username) is None:
            if messagebox.askyesno(
                languages.get_text("msg_user_not_exist", lang),
                languages.get_text("msg_user_not_reg", lang),
            ):
                self.open_register()
            return

        if authenticate_user(username, password):
            set_current_user(username)
            save_credentials(username, password, self.remember_var.get())
            messagebox.showinfo(
                languages.get_text("title_success", lang),
                languages.get_text("msg_welcome_user", lang).format(username),
            )
            self.login_success = True
            self.destroy()
        else:
            messagebox.showerror(
                languages.get_text("title_login_fail", lang),
                languages.get_text("msg_pass_wrong", lang),
            )

    def open_register(self):
        RegisterWindow(self, language=self.current_language)

    def open_change_password(self):
        current_user = self.username_var.get().strip()
        ChangePasswordWindow(
            self, default_username=current_user, language=self.current_language
        )


if __name__ == "__main__":
    app = LoginApp()
    app.mainloop()
