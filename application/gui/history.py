import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime
import sys
import os
import webbrowser

CURRENT_DIR = Path(__file__).resolve().parent
APP_DIR = CURRENT_DIR.parent
PROJECT_ROOT = APP_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.append(str(APP_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from application.gui import styles
from application.gui import languages

try:
    from data.dataloader import get_current_user, get_user_history, get_user_by_username
except ImportError:
    sys.path.append(str(APP_DIR))
    from data.dataloader import get_current_user, get_user_history, get_user_by_username


class History(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.create_widgets()

        self.load_data()

    def on_show(self):
        self.load_data()

    def create_widgets(self):
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=20, pady=20)

        self.title_label = ttk.Label(
            header_frame,
            text=languages.get_text("history_title", self.controller.current_language),
            font=styles.FONT_TITLE_CN,
        )
        self.title_label.pack(side=tk.LEFT)

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        columns = ("id", "time", "path")
        self.tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", yscrollcommand=scrollbar.set
        )

        self.tree.heading(
            "id", text=languages.get_text("col_id", self.controller.current_language)
        )
        self.tree.heading(
            "time",
            text=languages.get_text("col_time", self.controller.current_language),
        )
        self.tree.heading(
            "path",
            text=languages.get_text("col_path", self.controller.current_language),
        )

        self.tree.column("id", width=50, anchor=tk.CENTER)
        self.tree.column("time", width=150, anchor=tk.CENTER)
        self.tree.column("path", width=500, anchor=tk.W)

        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.columnconfigure(2, weight=1)

        self.open_folder_btn = ttk.Button(
            btn_frame,
            text=languages.get_text(
                "btn_open_folder", self.controller.current_language
            ),
            command=self.open_folder,
        )
        self.open_folder_btn.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.view_report_btn = ttk.Button(
            btn_frame,
            text=languages.get_text(
                "btn_view_report", self.controller.current_language
            ),
            command=self.view_report,
        )
        self.view_report_btn.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        self.refresh_btn = ttk.Button(
            btn_frame,
            text=languages.get_text("btn_refresh", self.controller.current_language),
            command=self.load_data,
        )
        self.refresh_btn.grid(row=0, column=2, sticky="ew")

        footer_frame = ttk.Frame(self)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(0, 12))
        self.footer_label = ttk.Label(
            footer_frame,
            text="",
            anchor="center",
        )
        self.footer_label.pack(fill=tk.X)
        self._set_footer_text()

    def update_language(self):
        lang = self.controller.current_language
        self.title_label.config(text=languages.get_text("history_title", lang))
        self.tree.heading("id", text=languages.get_text("col_id", lang))
        self.tree.heading("time", text=languages.get_text("col_time", lang))
        self.tree.heading("path", text=languages.get_text("col_path", lang))
        self.open_folder_btn.config(text=languages.get_text("btn_open_folder", lang))
        self.view_report_btn.config(text=languages.get_text("btn_view_report", lang))
        self.refresh_btn.config(text=languages.get_text("btn_refresh", lang))
        self._set_footer_text()

    def _set_footer_text(self):
        lang = getattr(self.controller, "current_language", "CN") or "CN"
        text = (
            "© LPDP-RiR Intelligent Medical Platform"
            if lang == "EN"
            else "© LPDP-RiR 智能医疗平台"
        )
        if hasattr(self, "footer_label"):
            self.footer_label.config(text=text)

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        username = get_current_user()
        if not username:
            return

        if not get_user_by_username(username):
            return

        history = get_user_history(username)

        output_root = APP_DIR / "output"

        for idx, foldername in enumerate(history, 1):
            try:
                dt = datetime.strptime(foldername, "%Y%m%d_%H%M%S")
                display_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                display_time = foldername

            full_path = output_root / foldername
            if full_path.exists():
                self.tree.insert("", tk.END, values=(idx, display_time, str(full_path)))
            else:
                self.tree.insert(
                    "",
                    tk.END,
                    values=(idx, display_time, str(full_path) + " [Missing]"),
                )

    def get_selected_path(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo(
                languages.get_text("title_info", self.controller.current_language),
                languages.get_text(
                    "msg_select_record", self.controller.current_language
                ),
            )
            return None

        item = self.tree.item(selected[0])
        path_str = item["values"][2]

        if path_str.endswith(" [Missing]"):
            path_str = path_str.replace(" [Missing]", "")

        path = Path(path_str)
        return path

    def open_folder(self):
        path = self.get_selected_path()
        if path:
            if path.exists():
                os.startfile(str(path))
            else:
                messagebox.showerror(
                    languages.get_text("title_error", self.controller.current_language),
                    languages.get_text(
                        "msg_folder_not_exist", self.controller.current_language
                    ),
                )

    def view_report(self):
        path = self.get_selected_path()
        if path:
            report_path = path / "report.html"
            if report_path.exists():
                webbrowser.open(str(report_path))
            else:
                messagebox.showerror(
                    languages.get_text("title_error", self.controller.current_language),
                    f"{languages.get_text('msg_report_not_found', self.controller.current_language)}: {report_path}",
                )


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1280x960")
    app = History(root, None)
    app.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
