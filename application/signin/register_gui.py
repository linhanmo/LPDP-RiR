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
    from application.data.dataloader import create_user
except ImportError:
    try:
        from data.dataloader import create_user
    except ImportError:
        from dataloader import create_user

from application.gui import styles, languages

try:
    from application.data.config_manager import (
        set_language,
        get_theme_index,
        set_theme_index,
    )
except ImportError:
    try:
        from data.config_manager import set_language, get_theme_index, set_theme_index
    except ImportError:

        def set_language(lang):
            pass

        def get_theme_index():
            return 0

        def set_theme_index(index):
            pass


class RegisterWindow(tk.Toplevel):
    def __init__(self, parent=None, language="CN"):
        super().__init__(parent)
        self.current_language = language
        self.title(languages.get_text("reg_title", self.current_language))
        self.geometry("500x400")
        self.resizable(False, False)

        try:
            icon_path = CURRENT_DIR.parent / "logo" / "logo.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception:
            pass

        self.center_window()
        self.create_widgets()
        self.apply_theme()

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
            text=languages.get_text("reg_title", self.current_language),
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

        confirm_frame = ttk.Frame(main_frame)
        confirm_frame.pack(fill=tk.X, pady=5)
        self.confirm_label = ttk.Label(
            confirm_frame,
            text=languages.get_text("label_confirm", self.current_language),
            width=10,
        )
        self.confirm_label.pack(side=tk.LEFT)
        self.confirm_var = tk.StringVar()
        self.confirm_entry = ttk.Entry(
            confirm_frame, textvariable=self.confirm_var, show="*"
        )
        self.confirm_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=20)

        self.register_btn = ttk.Button(
            btn_frame,
            text=languages.get_text("btn_register", self.current_language),
            command=self.on_register,
        )
        self.register_btn.pack(fill=tk.X, pady=(0, 10))

        self.login_link = ttk.Label(
            main_frame,
            text=languages.get_text("link_login", self.current_language),
            foreground="blue",
            cursor="hand2",
        )
        self.login_link.pack()
        self.login_link.bind("<Button-1>", lambda e: self.destroy())

    def switch_language(self):
        self.current_language = "EN" if self.current_language == "CN" else "CN"
        set_language(self.current_language)
        self.update_language()

    def update_language(self):
        lang = self.current_language
        self.title(languages.get_text("reg_title", lang))
        self.lang_btn.config(text=languages.get_text("lang_switch", lang))
        self.lang_label.config(text=languages.get_text("label_language", lang))
        self.theme_label.config(text=languages.get_text("label_theme", lang))

        current_idx = self.theme_combo.current()
        theme_names = [languages.get_text(key, lang) for key in styles.THEME_KEYS]
        self.theme_combo["values"] = theme_names
        if current_idx >= 0:
            self.theme_combo.current(current_idx)

        self.title_label.config(text=languages.get_text("reg_title", lang))
        self.user_label.config(text=languages.get_text("label_username", lang))
        self.pass_label.config(text=languages.get_text("label_password", lang))
        self.confirm_label.config(text=languages.get_text("label_confirm", lang))
        self.register_btn.config(text=languages.get_text("btn_register", lang))
        self.login_link.config(text=languages.get_text("link_login", lang))

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
        style.configure("TEntry", fieldbackground="white")

        if hasattr(self, "top_btn_frame"):
            self.top_btn_frame.configure(bg=bg_color)
        if hasattr(self, "lang_label"):
            self.lang_label.configure(bg=bg_color)
        if hasattr(self, "theme_label"):
            self.theme_label.configure(bg=bg_color)
        if hasattr(self, "lang_btn"):
            self.lang_btn.configure(bg=bg_color, activebackground=bg_color)

    def on_register(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        confirm = self.confirm_var.get()
        lang = self.current_language

        if not username:
            messagebox.showerror(
                languages.get_text("title_error", lang),
                languages.get_text("msg_enter_username", lang),
            )
            return
        if not password:
            messagebox.showerror(
                languages.get_text("title_error", lang),
                languages.get_text("msg_enter_password", lang),
            )
            return
        if password != confirm:
            messagebox.showerror(
                languages.get_text("title_error", lang),
                languages.get_text("msg_pass_mismatch", lang),
            )
            return

        if create_user(username, password):
            messagebox.showinfo(
                languages.get_text("title_success", lang),
                languages.get_text("msg_reg_success", lang).format(username),
            )
            if self.master and hasattr(self.master, "username_var"):
                self.master.username_var.set(username)
                if hasattr(self.master, "password_entry"):
                    self.master.password_entry.focus_set()
            self.destroy()
        else:
            messagebox.showerror(
                languages.get_text("title_error", lang),
                languages.get_text("msg_reg_fail", lang),
            )


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    app = RegisterWindow(root)
    root.wait_window(app)
    root.destroy()
