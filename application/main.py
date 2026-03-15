import tkinter as tk
from tkinter import ttk
from pathlib import Path
import sys
import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

try:
    import torch
except ImportError:
    pass

CURRENT_DIR = Path(__file__).resolve().parent
APP_DIR = CURRENT_DIR
if str(APP_DIR) not in sys.path:
    sys.path.append(str(APP_DIR))
if str(APP_DIR.parent) not in sys.path:
    sys.path.append(str(APP_DIR.parent))

try:
    from application.gui.navbar import NavigationBar
    from application.gui.homepage import Homepage
    from application.gui.introduction import Introduction
    from application.model.model_gui import ModelInterface
    from application.gui.history import History
    from application.gui import languages
    from application.data.config_manager import (
        get_language,
        set_language,
        get_theme_index,
        set_theme_index,
    )
    from application.gui import styles

except ImportError:
    sys.path.append(str(APP_DIR.parent))
    from application.gui.navbar import NavigationBar
    from application.gui.homepage import Homepage
    from application.gui.introduction import Introduction
    from application.model.model_gui import ModelInterface
    from application.gui.history import History
    from application.gui import languages
    from application.data.config_manager import (
        get_language,
        set_language,
        get_theme_index,
        set_theme_index,
    )
    from application.gui import styles


class MainApp(tk.Tk):
    def __init__(self, language="CN"):
        super().__init__()
        self.current_language = language
        self.title("LPDP-RiR System")
        self.geometry("1280x960")

        try:
            icon_path = APP_DIR / "logo" / "logo.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception:
            pass

        self.center_window()
        self.apply_theme()

        self.container = tk.Frame(self)
        self.container.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        self.navbar = NavigationBar(self, self)
        self.navbar.pack(side=tk.TOP, fill=tk.X)

        self.frames = {}
        self.pages = {
            "Homepage": Homepage,
            "Introduction": Introduction,
            "ModelInterface": ModelInterface,
            "History": History,
        }

        for name, F in self.pages.items():
            frame = F(parent=self.container, controller=self)
            self.frames[name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self._active_frame = None
        self.bind_all("<MouseWheel>", self._on_global_mousewheel)

        self.show_frame("Homepage")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        self.navbar.update_active_button(page_name)
        self._active_frame = frame
        if hasattr(frame, "on_show"):
            try:
                frame.on_show()
            except Exception:
                pass

    def _on_global_mousewheel(self, event):
        try:
            if isinstance(event.widget, ttk.Treeview):
                return
        except Exception:
            pass
        frame = getattr(self, "_active_frame", None)
        if frame and hasattr(frame, "on_mousewheel"):
            try:
                frame.on_mousewheel(event)
            except Exception:
                pass

    def switch_language(self):
        self.current_language = "EN" if self.current_language == "CN" else "CN"
        set_language(self.current_language)
        self.navbar.update_language()
        for frame in self.frames.values():
            if hasattr(frame, "update_language"):
                frame.update_language()

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

    def apply_theme(self):
        theme_index = get_theme_index()
        bg_color = styles.THEME_COLORS[theme_index]["hex"]
        self.configure(bg=bg_color)

        style = ttk.Style()
        style.configure(".", background=bg_color)
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color)
        style.configure("TButton", background=bg_color)
        style.configure("Treeview", fieldbackground="white")
        style.configure("TEntry", fieldbackground="white")

        if hasattr(self, "container"):
            self.container.configure(bg=bg_color)
        if hasattr(self, "navbar"):
            self.navbar.configure(bg=bg_color)
            if hasattr(self.navbar, "nav_frame"):
                self.navbar.nav_frame.configure(bg=bg_color)
            if hasattr(self.navbar, "btn_frame"):
                self.navbar.btn_frame.configure(bg=bg_color)
            if hasattr(self.navbar, "lang_label"):
                self.navbar.lang_label.configure(bg=bg_color)
            if hasattr(self.navbar, "theme_label"):
                self.navbar.theme_label.configure(bg=bg_color)

        if hasattr(self, "frames"):
            for frame in self.frames.values():
                frame.configure(bg=bg_color)

    def switch_theme(self):
        current_index = get_theme_index()
        new_index = (current_index + 1) % len(styles.THEME_COLORS)
        set_theme_index(new_index)
        self.apply_theme()


if __name__ == "__main__":
    try:
        from application.signin.login_gui import LoginApp
        from application.signin.changepassword_gui import ChangePasswordWindow
        from application.data.dataloader import get_current_user, verify_data_integrity
    except ImportError:
        from signin.login_gui import LoginApp
        from signin.changepassword_gui import ChangePasswordWindow
        from data.dataloader import get_current_user, verify_data_integrity

    try:
        verify_data_integrity()
    except Exception as e:
        print(f"Data integrity check failed: {e}")

    next_action = "login"
    current_language = get_language()

    while True:
        if next_action == "login":
            login_app = LoginApp(language=current_language)
            login_app.mainloop()

            if getattr(login_app, "current_language", None):
                current_language = login_app.current_language

            if getattr(login_app, "login_success", False):
                next_action = "main"
            else:
                break

        elif next_action == "main":
            app = MainApp(language=current_language)
            app.mainloop()

            if getattr(app, "current_language", None):
                current_language = app.current_language

            if getattr(app, "logout_requested", False):
                next_action = "login"
            elif getattr(app, "change_password_requested", False):
                next_action = "change_password"
            else:
                break

        elif next_action == "change_password":
            root = tk.Tk()
            root.withdraw()

            current_user = get_current_user() or ""
            cp_window = ChangePasswordWindow(
                root, default_username=current_user, language=current_language
            )

            def on_close():
                root.destroy()

            cp_window.protocol("WM_DELETE_WINDOW", on_close)

            root.wait_window(cp_window)

            if getattr(cp_window, "current_language", None):
                current_language = cp_window.current_language

            if getattr(cp_window, "change_success", False):
                next_action = "login"
            else:
                next_action = "main"

            try:
                root.destroy()
            except tk.TclError:
                pass
