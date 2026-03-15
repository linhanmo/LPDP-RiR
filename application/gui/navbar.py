import tkinter as tk
from tkinter import ttk
import sys
import subprocess
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
APP_DIR = CURRENT_DIR.parent
PROJECT_ROOT = APP_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from application.gui import styles
from application.gui import languages

try:
    from application.data.config_manager import get_theme_index, set_theme_index
except ImportError:
    try:
        from data.config_manager import get_theme_index, set_theme_index
    except ImportError:

        def get_theme_index():
            return 0

        def set_theme_index(index):
            pass


try:
    from application.data.dataloader import get_current_user
except ImportError:

    def get_current_user():
        return "Unknown User"


class NavigationBar(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.buttons = {}
        self.button_wrappers = {}
        self.create_widgets()

    def create_widgets(self):
        self.nav_frame = tk.Frame(self)
        self.nav_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        self.btn_frame = tk.Frame(self.nav_frame)
        self.btn_frame.pack(side=tk.RIGHT)

        self.pages = [
            ("nav_home", "Homepage"),
            ("nav_intro", "Introduction"),
            ("nav_model", "ModelInterface"),
            ("nav_history", "History"),
        ]

        self._nav_click_fx = {
            "Homepage": "pulse",
            "Introduction": "pulse",
            "ModelInterface": "pulse",
            "History": "pulse",
        }

        for key, page_key in self.pages:
            text = languages.get_text(key, self.controller.current_language)
            wrap = tk.Frame(
                self.btn_frame,
                bg="#FFFFFF",
                highlightthickness=1,
                highlightbackground="#243041",
            )
            wrap.pack(side=tk.LEFT, padx=2)
            btn = tk.Button(
                wrap,
                text=text,
                font=styles.FONT_BUTTON_CN,
                relief=tk.FLAT,
                bd=0,
                padx=15,
                pady=5,
                bg="#FFFFFF",
                fg="#000000",
                activebackground="#E6E6E6",
                activeforeground="#000000",
                command=lambda k=page_key: self._on_nav_click(k),
            )
            btn.pack()
            self.buttons[page_key] = btn
            self.button_wrappers[page_key] = wrap

        self.lang_label = tk.Label(
            self.btn_frame,
            text=languages.get_text("label_language", self.controller.current_language),
            font=styles.FONT_LABEL_BOLD_CN,
        )
        self.lang_label.pack(side=tk.LEFT, padx=(10, 2))

        lang_text = languages.get_text("lang_switch", self.controller.current_language)
        self.lang_btn = tk.Button(
            self.btn_frame,
            text=lang_text,
            font=styles.FONT_BUTTON_CN,
            relief=tk.FLAT,
            padx=10,
            command=self.controller.switch_language,
        )
        self.lang_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.theme_label = tk.Label(
            self.btn_frame,
            text=languages.get_text("label_theme", self.controller.current_language),
            font=styles.FONT_LABEL_BOLD_CN,
        )
        self.theme_label.pack(side=tk.LEFT, padx=(10, 2))

        theme_names = [
            languages.get_text(key, self.controller.current_language)
            for key in styles.THEME_KEYS
        ]
        self.theme_combo = ttk.Combobox(
            self.btn_frame,
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

        self.theme_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.theme_combo.bind("<<ComboboxSelected>>", self.on_theme_selected)

        username = get_current_user() or languages.get_text(
            "nav_not_logged_in", self.controller.current_language
        )

        self.user_menubutton = tk.Menubutton(
            self.btn_frame,
            text=username,
            font=styles.FONT_BUTTON_CN,
            relief=tk.FLAT,
            padx=10,
            bg="#f0f0f0",
            activebackground="#e0e0e0",
        )
        self.user_menu = tk.Menu(self.user_menubutton, tearoff=0)
        self.user_menubutton.configure(menu=self.user_menu)

        self.user_menu.add_command(
            label=languages.get_text("nav_logout", self.controller.current_language),
            command=self.logout,
        )
        self.user_menu.add_command(
            label=languages.get_text(
                "nav_change_password", self.controller.current_language
            ),
            command=self.change_password,
        )

        self.user_menubutton.pack(side=tk.LEFT, padx=20)

        self.separator = ttk.Separator(self, orient="horizontal")
        self.separator.pack(side=tk.TOP, fill=tk.X, pady=(5, 0))

    def _on_nav_click(self, page_key: str):
        wrap = self.button_wrappers.get(page_key)
        if wrap is not None:
            kind = self._nav_click_fx.get(page_key, "pulse")
            if kind:
                self._play_click_fx(wrap, kind)
        self.after(10, lambda: self.controller.show_frame(page_key))

    def _play_click_fx(self, stage: tk.Widget, kind: str):
        try:
            stage.update_idletasks()
            w = int(stage.winfo_width())
            h = int(stage.winfo_height())
        except Exception:
            return

        canvas = tk.Canvas(
            stage,
            bg=stage.cget("bg"),
            highlightthickness=0,
            bd=0,
        )
        canvas.place(x=0, y=0, relwidth=1, relheight=1)
        try:
            canvas.lift()
        except Exception:
            pass

        if kind == "pulse":
            self._fx_pulse(canvas, max(1, w), max(1, h), duration_ms=520)
        elif kind == "ripple":
            self._fx_ripple_grid(canvas, max(1, w), max(1, h), duration_ms=650)
        elif kind == "scan":
            self._fx_grid_scan(canvas, max(1, w), max(1, h), duration_ms=650)
        elif kind == "prism":
            self._fx_prism(canvas, max(1, w), max(1, h), duration_ms=650)
        else:
            try:
                canvas.destroy()
            except Exception:
                pass
            return

        canvas.after(700, lambda: canvas.winfo_exists() and canvas.destroy())

    def _fx_pulse(self, canvas: tk.Canvas, w: int, h: int, duration_ms: int):
        cx, cy = w * 0.5, h * 0.5
        dot = canvas.create_oval(0, 0, 0, 0, fill="#475569", outline="")
        ring = canvas.create_oval(0, 0, 0, 0, outline="#64748B", width=2)
        import time

        t0 = time.perf_counter()

        def tick():
            if not canvas.winfo_exists():
                return
            t = (time.perf_counter() - t0) * 1000.0
            p = min(1.0, max(0.0, t / max(1.0, float(duration_ms))))
            r = 4.0
            canvas.coords(dot, cx - r, cy - r, cx + r, cy + r)
            mx = float(min(w, h))
            rr = (mx * 0.14) + (mx * 0.42) * (p * p)
            canvas.coords(ring, cx - rr, cy - rr, cx + rr, cy + rr)
            if p < 1.0:
                a = max(0.0, 1.0 - p)
                width = 1 + int(round(2 * a))
                canvas.itemconfigure(ring, width=width, stipple="gray75")
                canvas.after(16, tick)
            else:
                try:
                    canvas.delete(dot)
                    canvas.delete(ring)
                except Exception:
                    pass

        tick()

    def _fx_ripple_grid(self, canvas: tk.Canvas, w: int, h: int, duration_ms: int):
        import time

        step = 20
        col = "#2A3444"
        for x in range(-step, w + step, step):
            canvas.create_line(x, 0, x, h, fill=col, width=1, stipple="gray75")
        for y in range(-step, h + step, step):
            canvas.create_line(0, y, w, y, fill=col, width=1, stipple="gray75")

        cx, cy = w * 0.5, h * 0.5
        ring = canvas.create_oval(cx, cy, cx, cy, outline="#67D1FF", width=2)
        t0 = time.perf_counter()

        def tick():
            if not canvas.winfo_exists():
                return
            t = (time.perf_counter() - t0) * 1000.0
            p = min(1.0, max(0.0, t / max(1.0, float(duration_ms))))
            e = 1.0 - (1.0 - p) * (1.0 - p)
            rr = 6.0 + (min(w, h) * 0.55) * e
            canvas.coords(ring, cx - rr, cy - rr, cx + rr, cy + rr)
            canvas.itemconfigure(
                ring, stipple="gray50", width=1 + int(round(2 * (1.0 - p)))
            )
            if p < 1.0:
                canvas.after(16, tick)
            else:
                try:
                    canvas.delete(ring)
                except Exception:
                    pass

        tick()

    def _fx_grid_scan(self, canvas: tk.Canvas, w: int, h: int, duration_ms: int):
        import time

        step = 18
        grid = "#243041"
        for x in range(0, w + step, step):
            canvas.create_line(x, 0, x, h, fill=grid, width=1, stipple="gray75")
        for y in range(0, h + step, step):
            canvas.create_line(0, y, w, y, fill=grid, width=1, stipple="gray75")

        band_h = max(10, int(h * 0.55))
        strips = 10
        strip_h = max(1, int(band_h / strips))
        bars = [
            canvas.create_rectangle(0, 0, 0, 0, outline="", fill="#67D1FF")
            for _ in range(strips)
        ]
        t0 = time.perf_counter()

        def tick():
            if not canvas.winfo_exists():
                return
            t = (time.perf_counter() - t0) * 1000.0
            p = min(1.0, max(0.0, t / max(1.0, float(duration_ms))))
            y_top = (-0.60 * h) + p * (2.20 * h)
            for i, it in enumerate(bars):
                y0 = y_top + i * strip_h
                y1 = y0 + strip_h + 1
                canvas.coords(it, 0, y0, w, y1)
                canvas.itemconfigure(it, stipple="gray75")
            if p < 1.0:
                canvas.after(16, tick)
            else:
                for it in bars:
                    try:
                        canvas.delete(it)
                    except Exception:
                        pass

        tick()

    def _fx_prism(self, canvas: tk.Canvas, w: int, h: int, duration_ms: int):
        import time
        import math

        cx, cy = w * 0.5, h * 0.5
        n = 22
        r = max(w, h) * 0.85
        wedges = [
            canvas.create_polygon(0, 0, 0, 0, 0, 0, fill="", outline="")
            for _ in range(n)
        ]
        cols = ["#67D1FF", "#9B7BFF", "#50FFC4", "#FF54C8"]
        t0 = time.perf_counter()

        def tick():
            if not canvas.winfo_exists():
                return
            t = (time.perf_counter() - t0) * 1000.0
            p = min(1.0, max(0.0, t / max(1.0, float(duration_ms))))
            rot = (p * 2.0) * math.pi
            step = 2 * math.pi / n
            for i, it in enumerate(wedges):
                a0 = rot + i * step
                a1 = a0 + step
                rr = r * (0.55 + 0.55 * p)
                pts = [
                    cx,
                    cy,
                    cx + math.cos(a0) * rr,
                    cy + math.sin(a0) * rr,
                    cx + math.cos(a1) * rr,
                    cy + math.sin(a1) * rr,
                ]
                canvas.coords(it, *pts)
                canvas.itemconfigure(it, fill=cols[i % len(cols)], stipple="gray75")
            if p < 1.0:
                canvas.after(16, tick)
            else:
                for it in wedges:
                    try:
                        canvas.delete(it)
                    except Exception:
                        pass

        tick()

    def update_active_button(self, page_name):
        for key, btn in self.buttons.items():
            wrap = self.button_wrappers.get(key)
            if key == page_name:
                btn.configure(
                    bg="#FFFFFF",
                    fg="#000000",
                    activebackground="#E6E6E6",
                    activeforeground="#000000",
                )
                if wrap is not None:
                    wrap.configure(highlightbackground="#67D1FF")
            else:
                btn.configure(
                    bg="#FFFFFF",
                    fg="#000000",
                    activebackground="#E6E6E6",
                    activeforeground="#000000",
                )
                if wrap is not None:
                    wrap.configure(highlightbackground="#243041")

    def update_language(self):
        lang = self.controller.current_language
        for key, page_key in self.pages:
            self.buttons[page_key].config(text=languages.get_text(key, lang))

        self.lang_btn.config(text=languages.get_text("lang_switch", lang))
        self.lang_label.config(text=languages.get_text("label_language", lang))
        self.theme_label.config(text=languages.get_text("label_theme", lang))

        current_idx = self.theme_combo.current()
        theme_names = [languages.get_text(key, lang) for key in styles.THEME_KEYS]
        self.theme_combo["values"] = theme_names
        if current_idx >= 0:
            self.theme_combo.current(current_idx)

        self.user_menu.entryconfigure(0, label=languages.get_text("nav_logout", lang))
        self.user_menu.entryconfigure(
            1, label=languages.get_text("nav_change_password", lang)
        )

        username = get_current_user() or languages.get_text("nav_not_logged_in", lang)
        self.user_menubutton.config(text=username)

    def on_theme_selected(self, event):
        selected_index = self.theme_combo.current()
        if selected_index >= 0:
            set_theme_index(selected_index)
            self.controller.apply_theme()

    def logout(self):
        self.controller.logout_requested = True
        self.controller.destroy()

    def change_password(self):
        self.controller.change_password_requested = True
        self.controller.destroy()
