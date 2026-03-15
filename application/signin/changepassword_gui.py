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
    from application.signin.changepassword import change_password
except ImportError:
    try:
        from signin.changepassword import change_password
    except ImportError:
        from changepassword import change_password

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


class ChangePasswordWindow(tk.Toplevel):
    def __init__(self, parent=None, default_username="", language="CN"):
        super().__init__(parent)
        self.current_language = language
        self.change_success = False
        self.title(languages.get_text("cp_title", self.current_language))
        self.geometry("500x400")
        self.resizable(False, False)

        try:
            icon_path = CURRENT_DIR.parent / "logo" / "logo.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception:
            pass

        self.default_username = default_username
        self.center_window()
        self.apply_theme()
        self.create_widgets()

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
            text=languages.get_text("cp_title", self.current_language),
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
        self.username_var = tk.StringVar(value=self.default_username)
        self.username_entry = ttk.Entry(user_frame, textvariable=self.username_var)
        self.username_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        if self.default_username:
            self.username_entry.config(state="readonly")

        old_frame = ttk.Frame(main_frame)
        old_frame.pack(fill=tk.X, pady=5)
        self.old_pass_label = ttk.Label(
            old_frame,
            text=languages.get_text("label_old_pass", self.current_language),
            width=10,
        )
        self.old_pass_label.pack(side=tk.LEFT)
        self.old_pass_var = tk.StringVar()
        self.old_pass_entry = ttk.Entry(
            old_frame, textvariable=self.old_pass_var, show="*"
        )
        self.old_pass_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        new_frame = ttk.Frame(main_frame)
        new_frame.pack(fill=tk.X, pady=5)
        self.new_pass_label = ttk.Label(
            new_frame,
            text=languages.get_text("label_new_pass", self.current_language),
            width=10,
        )
        self.new_pass_label.pack(side=tk.LEFT)
        self.new_pass_var = tk.StringVar()
        self.new_pass_entry = ttk.Entry(
            new_frame, textvariable=self.new_pass_var, show="*"
        )
        self.new_pass_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        confirm_frame = ttk.Frame(main_frame)
        confirm_frame.pack(fill=tk.X, pady=5)
        self.confirm_label = ttk.Label(
            confirm_frame,
            text=languages.get_text("label_confirm_new", self.current_language),
            width=10,
        )
        self.confirm_label.pack(side=tk.LEFT)
        self.confirm_pass_var = tk.StringVar()
        self.confirm_pass_entry = ttk.Entry(
            confirm_frame, textvariable=self.confirm_pass_var, show="*"
        )
        self.confirm_pass_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=20)

        self.change_btn = ttk.Button(
            btn_frame,
            text=languages.get_text("btn_change_pass", self.current_language),
            command=self.on_change,
        )
        self.change_btn.pack(fill=tk.X, pady=(0, 10))

        self.back_btn = ttk.Button(
            btn_frame,
            text=languages.get_text("btn_back", self.current_language),
            command=self.destroy,
        )
        self.back_btn.pack(fill=tk.X)

    def switch_language(self):
        self.current_language = "EN" if self.current_language == "CN" else "CN"
        set_language(self.current_language)
        self.update_language()

    def update_language(self):
        lang = self.current_language
        self.title(languages.get_text("cp_title", lang))
        self.lang_btn.config(text=languages.get_text("lang_switch", lang))
        self.lang_label.config(text=languages.get_text("label_language", lang))
        self.theme_label.config(text=languages.get_text("label_theme", lang))

        current_idx = self.theme_combo.current()
        theme_names = [languages.get_text(key, lang) for key in styles.THEME_KEYS]
        self.theme_combo["values"] = theme_names
        if current_idx >= 0:
            self.theme_combo.current(current_idx)

        self.title_label.config(text=languages.get_text("cp_title", lang))
        self.user_label.config(text=languages.get_text("label_username", lang))
        self.old_pass_label.config(text=languages.get_text("label_old_pass", lang))
        self.new_pass_label.config(text=languages.get_text("label_new_pass", lang))
        self.confirm_label.config(text=languages.get_text("label_confirm_new", lang))
        self.change_btn.config(text=languages.get_text("btn_change_pass", lang))
        self.back_btn.config(text=languages.get_text("btn_back", lang))

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
        if hasattr(self, "theme_btn"):
            self.theme_btn.configure(bg=bg_color, activebackground=bg_color)

    def on_change(self):
        username = self.username_var.get().strip()
        old_pass = self.old_pass_var.get()
        new_pass = self.new_pass_var.get()
        confirm_pass = self.confirm_pass_var.get()
        lang = self.current_language

        if not username:
            messagebox.showerror(
                languages.get_text("title_error", lang),
                languages.get_text("msg_enter_username", lang),
            )
            return
        if not old_pass:
            messagebox.showerror(
                languages.get_text("title_error", lang),
                languages.get_text("msg_enter_old_pass", lang),
            )
            return
        if not new_pass:
            messagebox.showerror(
                languages.get_text("title_error", lang),
                languages.get_text("msg_enter_new_pass", lang),
            )
            return
        if new_pass != confirm_pass:
            messagebox.showerror(
                languages.get_text("title_error", lang),
                languages.get_text("msg_new_pass_mismatch", lang),
            )
            return

        if change_password(username, old_pass, new_pass):
            messagebox.showinfo(
                languages.get_text("title_success", lang),
                languages.get_text("msg_change_pass_success", lang),
            )
            self.change_success = True
            if self.master and hasattr(self.master, "password_var"):
                self.master.password_var.set("")
                if hasattr(self.master, "password_entry"):
                    self.master.password_entry.focus_set()
            self.destroy()
        else:
            messagebox.showerror(
                languages.get_text("title_error", lang),
                languages.get_text("msg_change_pass_fail", lang),
            )


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    app = ChangePasswordWindow(root)
    root.wait_window(app)
    root.destroy()
