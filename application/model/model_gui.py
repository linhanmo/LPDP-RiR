import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import sys
import os
import threading
import numpy as np
from PIL import Image, ImageTk
import glob
import shutil
import subprocess
from datetime import datetime
import re
import math
import time

CURRENT_DIR = Path(__file__).resolve().parent
APP_DIR = CURRENT_DIR.parent
PROJECT_ROOT = APP_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
if str(APP_DIR) not in sys.path:
    sys.path.append(str(APP_DIR))

ACX_UNET_DIR = APP_DIR / "ACX-UNET"
if str(ACX_UNET_DIR) not in sys.path:
    sys.path.append(str(ACX_UNET_DIR))

try:
    from gui import styles
    from gui import languages
except ImportError:
    pass

try:
    from model.model import (
        load_3d_data,
        load_model,
        infer_full_volume,
        generate_report,
        slices_from_volume,
        save_image,
        save_image_rgb,
        to_cdhw,
        colorize_mask,
        heatmap_rgb,
        postprocess_binary,
        stretch_to_uint8,
        normalize_to_uint8,
        window_to_uint8,
        equalize_hist_u8,
        run_analysis_and_save,
    )
except ImportError:
    try:
        from model import (
            load_3d_data,
            load_model,
            infer_full_volume,
            generate_report,
            slices_from_volume,
            save_image,
            save_image_rgb,
            to_cdhw,
            colorize_mask,
            heatmap_rgb,
            postprocess_binary,
            stretch_to_uint8,
            normalize_to_uint8,
            window_to_uint8,
            equalize_hist_u8,
            run_analysis_and_save,
        )
    except ImportError as e:
        print(f"Error importing model: {e}")


def _attach_magnetic_button(stage: tk.Widget, btn: tk.Widget):
    def clamp(v: float, lo: float, hi: float):
        return lo if v < lo else hi if v > hi else v

    target_x = 0.0
    target_y = 0.0
    cur_x = 0.0
    cur_y = 0.0
    after_id = None

    def loop():
        nonlocal cur_x, cur_y, after_id
        try:
            if not stage.winfo_exists() or not btn.winfo_exists():
                after_id = None
                return
        except Exception:
            after_id = None
            return

        cur_x += (target_x - cur_x) * 0.12
        cur_y += (target_y - cur_y) * 0.12
        try:
            btn.place_configure(x=int(round(cur_x)), y=int(round(cur_y)))
        except Exception:
            after_id = None
            return

        if (
            abs(target_x) < 0.2
            and abs(target_y) < 0.2
            and abs(cur_x) < 0.2
            and abs(cur_y) < 0.2
        ):
            try:
                btn.place_configure(x=0, y=0)
            except Exception:
                pass
            after_id = None
            return

        after_id = stage.after(16, loop)

    def on_move(e):
        nonlocal target_x, target_y, after_id
        try:
            srw = stage.winfo_width()
            srh = stage.winfo_height()
            brx = btn.winfo_rootx()
            bry = btn.winfo_rooty()
            bw = btn.winfo_width()
            bh = btn.winfo_height()
        except Exception:
            return

        cx = brx + bw * 0.5
        cy = bry + bh * 0.5
        dx = float(e.x_root) - cx
        dy = float(e.y_root) - cy
        dist = math.hypot(dx, dy)
        max_dist = max(90.0, min(float(srw), float(srh)) * 0.38)
        k = clamp(1.0 - dist / max_dist, 0.0, 1.0)
        target_x = dx * 0.14 * k
        target_y = dy * 0.14 * k
        if after_id is None:
            after_id = stage.after(16, loop)

    def on_leave(_e=None):
        nonlocal target_x, target_y, after_id
        target_x = 0.0
        target_y = 0.0
        if after_id is None:
            after_id = stage.after(16, loop)

    def on_destroy(_e=None):
        nonlocal after_id
        if after_id is not None:
            try:
                stage.after_cancel(after_id)
            except Exception:
                pass
            after_id = None

    stage.bind("<Motion>", on_move, add="+")
    stage.bind("<Leave>", on_leave, add="+")
    btn.bind("<Motion>", on_move, add="+")
    btn.bind("<Leave>", on_leave, add="+")
    stage.bind("<Destroy>", on_destroy, add="+")


class ProgressRingDialog(tk.Toplevel):
    def __init__(self, parent, title: str, message: str):
        super().__init__(parent.winfo_toplevel())
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.overrideredirect(True)
        try:
            self.attributes("-topmost", True)
        except Exception:
            pass

        self._transparent_color = "#010101"
        self.configure(bg=self._transparent_color)
        try:
            self.wm_attributes("-transparentcolor", self._transparent_color)
        except Exception:
            pass

        self._anim_after_id = None
        self._indeterminate = False
        self._t0 = time.perf_counter()

        self._bg = "#0B1220"
        self._border = "#243041"
        self._track = "#243041"
        self._text = "#FFFFFF"
        self._subtext = "#B8C0CC"
        self._grad_a = (103, 209, 255)
        self._grad_b = (155, 123, 255)

        self._size = 220
        self._pad = 16
        self._ring_cy = 92
        self._r0 = 56
        self._lw = 10
        self._segments = 60
        self._seg_ids = []

        self.message_var = tk.StringVar(value=message)

        self.canvas = tk.Canvas(
            self,
            width=self._size,
            height=self._size,
            highlightthickness=0,
            bg=self._transparent_color,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self._bg_id = None
        self._track_id = None
        self._text_id = None
        self._msg_id = None

        self._draw_static()
        self._set_progress_value(0.0)

        self.update_idletasks()
        self._center_on_parent(parent.winfo_toplevel())
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
        except Exception:
            pass
        self.grab_set()

    def _center_on_parent(self, root):
        try:
            root.update_idletasks()
            rx = root.winfo_rootx()
            ry = root.winfo_rooty()
            rw = root.winfo_width()
            rh = root.winfo_height()
            w = self.winfo_width()
            h = self.winfo_height()
            x = int(rx + (rw - w) / 2)
            y = int(ry + (rh - h) / 2)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _mix_hex(self, a: tuple[int, int, int], b: tuple[int, int, int], t: float):
        t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
        r = int(round(a[0] + (b[0] - a[0]) * t))
        g = int(round(a[1] + (b[1] - a[1]) * t))
        bb = int(round(a[2] + (b[2] - a[2]) * t))
        return f"#{r:02X}{g:02X}{bb:02X}"

    def _rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        r = max(0, min(r, int((x2 - x1) / 2), int((y2 - y1) / 2)))
        points = [
            x1 + r,
            y1,
            x2 - r,
            y1,
            x2,
            y1,
            x2,
            y1 + r,
            x2,
            y2 - r,
            x2,
            y2,
            x2 - r,
            y2,
            x1 + r,
            y2,
            x1,
            y2,
            x1,
            y2 - r,
            x1,
            y1 + r,
            x1,
            y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def _draw_static(self):
        self.canvas.delete("all")
        self._bg_id = self._rounded_rect(
            0,
            0,
            self._size,
            self._size,
            16,
            fill=self._bg,
            outline=self._border,
            width=1,
        )

        cx = self._size / 2
        cy = self._ring_cy
        x1 = cx - self._r0
        y1 = cy - self._r0
        x2 = cx + self._r0
        y2 = cy + self._r0

        self._bbox = (x1, y1, x2, y2)
        self._track_id = self.canvas.create_oval(
            *self._bbox, outline=self._track, width=self._lw
        )
        self._text_id = self.canvas.create_text(
            cx,
            cy,
            text="0%",
            fill=self._text,
            font=("Segoe UI", int(max(12, round(self._r0 * 0.55))), "bold"),
        )
        self._msg_id = self.canvas.create_text(
            cx,
            cy + self._r0 + 26,
            text=self.message_var.get(),
            fill=self._subtext,
            font=("Segoe UI", 11),
            width=self._size - self._pad * 2,
            justify="center",
        )

    def _set_progress_value(self, p: float):
        p = 0.0 if p < 0.0 else 1.0 if p > 1.0 else p
        for seg_id in self._seg_ids:
            try:
                self.canvas.delete(seg_id)
            except Exception:
                pass
        self._seg_ids = []

        if self._bbox is None:
            return

        seg = 360.0 / float(self._segments)
        k = int(round(self._segments * p))
        if k <= 0:
            self.canvas.itemconfigure(self._text_id, text=f"{int(round(p * 100))}%")
            return

        for i in range(k):
            tt = i / float(max(1, k - 1))
            col = self._mix_hex(self._grad_a, self._grad_b, tt)
            start = 90.0 - seg * i
            arc_id = self.canvas.create_arc(
                *self._bbox,
                start=start,
                extent=-seg * 1.02,
                style="arc",
                outline=col,
                width=self._lw,
            )
            self._seg_ids.append(arc_id)
        self.canvas.itemconfigure(self._text_id, text=f"{int(round(p * 100))}%")

    def set_progress(self, current: int, total: int, message: str | None = None):
        if total is None or int(total) <= 0:
            return

        self._stop_animation()
        self._indeterminate = False

        cur = max(0, min(int(current), int(total)))
        p = cur / float(int(total))
        self._set_progress_value(p)
        if message is not None:
            self.message_var.set(message)
            self.canvas.itemconfigure(self._msg_id, text=self.message_var.get())

    def set_indeterminate(self, message: str | None = None):
        if message is not None:
            self.message_var.set(message)
            self.canvas.itemconfigure(self._msg_id, text=self.message_var.get())
        if self._indeterminate:
            return
        self._indeterminate = True
        self._t0 = time.perf_counter()
        self._animate()

    def _animate(self):
        if not self._indeterminate:
            return
        t = time.perf_counter() - self._t0
        p = 0.35 + 0.55 * (0.5 + 0.5 * math.sin(t * 1.15))
        self._set_progress_value(p)
        self._anim_after_id = self.after(30, self._animate)

    def _stop_animation(self):
        if self._anim_after_id is not None:
            try:
                self.after_cancel(self._anim_after_id)
            except Exception:
                pass
            self._anim_after_id = None

    def close(self):
        self._indeterminate = False
        self._stop_animation()
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass


class TypingDotsDialog(tk.Toplevel):
    def __init__(
        self,
        parent,
        title: str,
        caption: str | None = None,
        on_close=None,
        duration_ms: int = 2000,
        interval_ms: int = 30,
    ):
        super().__init__(parent.winfo_toplevel())
        self.title(title)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.overrideredirect(True)
        try:
            self.attributes("-topmost", True)
        except Exception:
            pass

        self._interval_ms = int(interval_ms)
        self._after_id = None
        self._close_after_id = None
        self._on_close = on_close
        self._t0 = time.perf_counter()
        self._period_s = 1.1
        self._phases_s = (0.0, 0.12, 0.24)

        self._transparent_color = "#010101"
        self.configure(bg=self._transparent_color)
        try:
            self.wm_attributes("-transparentcolor", self._transparent_color)
        except Exception:
            pass

        container = tk.Frame(self, bg=self._transparent_color)
        container.pack(fill=tk.BOTH, expand=True)

        pad = 14
        inner_bg = "#0B1220"
        inner = tk.Frame(container, bg=inner_bg, padx=pad, pady=pad)
        inner.pack()

        self.canvas = tk.Canvas(
            inner, width=68, height=24, highlightthickness=0, bg=inner_bg
        )
        self.canvas.pack()

        if caption:
            self.caption_label = tk.Label(
                inner,
                text=caption,
                bg=inner_bg,
                fg="#B8C0CC",
                font=("Segoe UI", 10),
            )
            self.caption_label.pack(pady=(10, 0))

        self._r = 3
        self._base_y = 12
        self._lift = 6
        xs = (22, 34, 46)
        colors = ("#E5E7EB", "#D1D5DB", "#9CA3AF")
        self._dots = []
        for x, c in zip(xs, colors):
            dot_id = self.canvas.create_oval(
                x - self._r,
                self._base_y - self._r,
                x + self._r,
                self._base_y + self._r,
                fill=c,
                outline="",
            )
            self._dots.append((dot_id, x))

        self.update_idletasks()
        self._center_on_parent(parent.winfo_toplevel())
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
        except Exception:
            pass
        self.grab_set()

        self._tick()
        self._close_after_id = self.after(int(duration_ms), self.close)

    def _center_on_parent(self, root):
        try:
            root.update_idletasks()
            rx = root.winfo_rootx()
            ry = root.winfo_rooty()
            rw = root.winfo_width()
            rh = root.winfo_height()
            w = self.winfo_width()
            h = self.winfo_height()
            x = int(rx + (rw - w) / 2)
            y = int(ry + (rh - h) / 2)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _tick(self):
        now = time.perf_counter()
        for (dot_id, x), phase in zip(self._dots, self._phases_s):
            t = (now - self._t0 - phase) % self._period_s
            p = t / self._period_s
            y = self._base_y - self._lift * math.sin(math.pi * p)
            self.canvas.coords(
                dot_id,
                x - self._r,
                y - self._r,
                x + self._r,
                y + self._r,
            )
        self._after_id = self.after(self._interval_ms, self._tick)

    def close(self):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        if self._close_after_id is not None:
            try:
                self.after_cancel(self._close_after_id)
            except Exception:
                pass
            self._close_after_id = None
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
        if callable(self._on_close):
            try:
                self._on_close()
            except Exception:
                pass


class ToastDialog(tk.Toplevel):
    def __init__(
        self,
        parent,
        message: str,
        button_text: str | None = None,
        on_button=None,
        on_close=None,
        duration_ms: int | None = None,
        lang: str | None = None,
    ):
        super().__init__(parent.winfo_toplevel())
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.overrideredirect(True)
        try:
            self.attributes("-topmost", True)
        except Exception:
            pass

        self._on_button = on_button
        self._on_close = on_close
        self._close_after_id = None
        self._anim_after_id = None
        self._target_x = 0
        self._target_y = 0

        self._toast_w = 320

        lang = (lang or "CN").upper()
        font_family = "Arial" if lang == "EN" else "Microsoft YaHei"

        bg = "#000000"
        border = "#111111"
        text = "#FFFFFF"
        muted = "#BFBFBF"

        self.configure(bg=bg)

        container = tk.Frame(
            self,
            bg=bg,
            highlightthickness=1,
            highlightbackground=border,
        )
        container.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(container, bg=bg, height=28)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        close_btn = tk.Button(
            header,
            text="×",
            command=self.close,
            bg=bg,
            fg=muted,
            activebackground=bg,
            activeforeground=text,
            relief="flat",
            bd=0,
            padx=6,
            pady=0,
            font=(font_family, 14, "bold"),
        )
        close_btn.pack(side=tk.RIGHT, padx=8, pady=4)

        body = tk.Frame(container, bg=bg, padx=12, pady=10)
        body.pack(fill=tk.BOTH, expand=True)

        msg_label = tk.Label(
            body,
            text=message,
            bg=bg,
            fg=text,
            font=(font_family, 12, "bold"),
            justify="left",
            anchor="w",
            wraplength=self._toast_w - 24,
        )
        msg_label.pack(fill=tk.X)

        if button_text:
            mag_stage = tk.Frame(body, bg=bg)
            mag_stage.pack(anchor="w", pady=(10, 0))
            btn = tk.Button(
                mag_stage,
                text=button_text,
                command=self._handle_button,
                bg="#FFFFFF",
                fg="#000000",
                activebackground="#E5E7EB",
                activeforeground="#000000",
                relief="flat",
                padx=10,
                pady=4,
                font=(font_family, 11, "bold"),
            )
            btn.place(relx=0.5, rely=0.5, anchor="center", x=0, y=0)
            btn.update_idletasks()
            mag_stage.configure(
                width=btn.winfo_reqwidth() + 24,
                height=btn.winfo_reqheight() + 24,
            )
            mag_stage.pack_propagate(False)
            _attach_magnetic_button(mag_stage, btn)

        self.update_idletasks()
        h = max(container.winfo_reqheight(), 56)
        self.geometry(f"{self._toast_w}x{int(h)}+0+0")
        self.update_idletasks()
        self._place_bottom_right(parent.winfo_toplevel())
        self.bind("<Escape>", lambda _e: self.close())
        try:
            self.deiconify()
            self.lift()
        except Exception:
            pass

        self._animate_in()
        if duration_ms is not None:
            try:
                self._close_after_id = self.after(int(duration_ms), self.close)
            except Exception:
                self._close_after_id = None

    def _place_bottom_right(self, root):
        try:
            root.update_idletasks()
            rx = root.winfo_rootx()
            ry = root.winfo_rooty()
            rw = root.winfo_width()
            rh = root.winfo_height()
            w = self.winfo_width()
            h = self.winfo_height()
            margin = 16
            self._target_x = int(rx + rw - w - margin)
            self._target_y = int(ry + rh - h - margin)
            self.geometry(f"+{self._target_x}+{self._target_y + 6}")
        except Exception:
            pass

    def _animate_in(self):
        steps = 11

        def _step(i: int):
            p = i / float(steps)
            e = 1 - (1 - p) * (1 - p)
            try:
                y = int(self._target_y + 6 * (1 - e))
                self.geometry(f"+{int(self._target_x)}+{y}")
            except Exception:
                pass
            if i < steps:
                self._anim_after_id = self.after(20, lambda: _step(i + 1))

        _step(0)

    def _handle_button(self):
        if callable(self._on_button):
            try:
                self._on_button()
            except Exception:
                pass
        self.close()

    def close(self):
        if self._close_after_id is not None:
            try:
                self.after_cancel(self._close_after_id)
            except Exception:
                pass
            self._close_after_id = None
        if self._anim_after_id is not None:
            try:
                self.after_cancel(self._anim_after_id)
            except Exception:
                pass
            self._anim_after_id = None
        try:
            self.destroy()
        except Exception:
            pass
        if callable(self._on_close):
            try:
                self._on_close()
            except Exception:
                pass


class ModelInterface(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._typing_dots_dialog = None
        self._report_toast = None

        self.input_dir = None
        self.output_dir = None
        self.last_imported_path = None
        self.current_vol = None
        self.current_slices = []
        self.result_dict = {}
        self.current_result_type = None
        self.current_slice_idx = 0
        self.is_analyzing = False

        self.init_ui()

    def _i18n_pick(self, value):
        lang = getattr(self.controller, "current_language", "CN")
        try:
            if isinstance(value, dict):
                if lang in value:
                    return str(value[lang])
                if "CN" in value:
                    return str(value["CN"])
                if "EN" in value:
                    return str(value["EN"])
                for v in value.values():
                    return str(v)
                return ""
            if isinstance(value, (tuple, list)) and len(value) == 2:
                return str(value[1] if lang == "EN" else value[0])
        except Exception:
            pass
        return "" if value is None else str(value)

    def _show_toast(
        self,
        message,
        duration_ms: int | None = None,
        button_text=None,
        on_button=None,
    ):
        if self._report_toast is not None:
            try:
                self._report_toast.close()
            except Exception:
                pass
            self._report_toast = None

        msg = self._i18n_pick(message)
        btn_text = self._i18n_pick(button_text) if button_text is not None else None

        self._report_toast = ToastDialog(
            self,
            message=msg,
            button_text=btn_text,
            on_button=on_button,
            on_close=lambda: setattr(self, "_report_toast", None),
            duration_ms=duration_ms,
            lang=getattr(self.controller, "current_language", "CN"),
        )

    def init_ui(self):

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        btn_frame = ttk.Frame(self, padding="10")
        btn_frame.grid(row=0, column=0, sticky="ew")

        self.buttons = {}
        buttons_data = [
            ("btn_import", self.on_import_data),
            ("btn_analyze", self.on_analyze_data),
            ("btn_visualize", self.on_visualize_3d),
            ("btn_unet", self.on_unet_analysis),
            ("btn_export", self.on_export_report),
        ]

        for key, cmd in buttons_data:
            text = languages.get_text(key, self.controller.current_language)
            if key in {
                "btn_import",
                "btn_analyze",
                "btn_visualize",
                "btn_unet",
                "btn_export",
            }:
                mag_stage = ttk.Frame(btn_frame)
                mag_stage.pack(side=tk.LEFT, padx=5)
                btn = ttk.Button(mag_stage, text=text, command=cmd)
                btn.place(relx=0.5, rely=0.5, anchor="center", x=0, y=0)
                btn.update_idletasks()
                mag_stage.configure(
                    width=btn.winfo_reqwidth() + 24,
                    height=btn.winfo_reqheight() + 24,
                )
                mag_stage.pack_propagate(False)
                _attach_magnetic_button(mag_stage, btn)
            else:
                btn = ttk.Button(btn_frame, text=text, command=cmd)
                btn.pack(side=tk.LEFT, padx=5)
            self.buttons[key] = btn

        mid_frame = ttk.Frame(self)
        mid_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        mid_frame.grid_columnconfigure(0, weight=1, uniform="mid_cols")
        mid_frame.grid_columnconfigure(1, weight=1, uniform="mid_cols")
        mid_frame.grid_rowconfigure(1, weight=1)

        in_header = ttk.Frame(mid_frame)
        in_header.grid(row=0, column=0, sticky="ew", padx=2, pady=(0, 2))
        self.in_header_label = ttk.Label(
            in_header,
            text=languages.get_text("header_input", self.controller.current_language),
            font=styles.FONT_LABEL_BOLD_CN,
        )
        self.in_header_label.pack(side=tk.LEFT)

        out_header = ttk.Frame(mid_frame)
        out_header.grid(row=0, column=1, sticky="ew", padx=2, pady=(0, 2))
        self.out_header_label = ttk.Label(
            out_header,
            text=languages.get_text("header_output", self.controller.current_language),
            font=styles.FONT_LABEL_BOLD_CN,
        )
        self.out_header_label.pack(side=tk.LEFT)

        self.result_type_combo = ttk.Combobox(out_header, state="readonly", width=15)
        self.result_type_combo.pack(side=tk.RIGHT)
        self.result_type_label = ttk.Label(
            out_header,
            text=languages.get_text(
                "label_result_type", self.controller.current_language
            ),
        )
        self.result_type_label.pack(side=tk.RIGHT, padx=5)
        self.result_type_combo.bind("<<ComboboxSelected>>", self.on_result_type_change)

        input_frame = ttk.Frame(mid_frame, borderwidth=1, relief="sunken")
        input_frame.grid(row=1, column=0, sticky="nsew", padx=2)

        self.input_canvas = tk.Canvas(input_frame, bg="white", highlightthickness=0)
        self.input_canvas.pack(fill=tk.BOTH, expand=True)

        output_frame = ttk.Frame(mid_frame, borderwidth=1, relief="sunken")
        output_frame.grid(row=1, column=1, sticky="nsew", padx=2)

        self.output_canvas = tk.Canvas(output_frame, bg="white", highlightthickness=0)
        self.output_canvas.pack(fill=tk.BOTH, expand=True)

        ctrl_frame = ttk.Frame(self)
        ctrl_frame.grid(row=2, column=0, sticky="ew", padx=10)

        ctrl_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ctrl_frame.columnconfigure(0, weight=1)
        ctrl_frame.columnconfigure(1, weight=1)

        slider_frame = ttk.Frame(ctrl_frame)
        slider_frame.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.slice_index_label = ttk.Label(
            slider_frame,
            text=languages.get_text(
                "label_slice_index", self.controller.current_language
            ),
        )
        self.slice_index_label.pack(side=tk.LEFT)
        self.slice_scale = ttk.Scale(
            slider_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            command=self.on_slice_change,
        )
        self.slice_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.slice_label = ttk.Label(slider_frame, text="0/0")
        self.slice_label.pack(side=tk.LEFT)

        desc_frame = ttk.Frame(ctrl_frame)
        desc_frame.grid(row=0, column=1, sticky="ew")

        self.desc_label_title = ttk.Label(
            desc_frame,
            text=languages.get_text(
                "label_description", self.controller.current_language
            ),
        )
        self.desc_label_title.pack(side=tk.LEFT)
        self.result_desc_label = ttk.Label(
            desc_frame,
            text=languages.get_text("desc_default", self.controller.current_language),
            relief="sunken",
            anchor="w",
            padding=(5, 2),
        )
        self.result_desc_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.report_frame = ttk.LabelFrame(
            self,
            text=languages.get_text("group_report", self.controller.current_language),
            height=150,
        )
        self.report_frame.grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=10
        )
        self.report_frame.grid_propagate(False)

        self.report_text = tk.Text(
            self.report_frame, wrap=tk.WORD, font=("Consolas", 10)
        )
        self.report_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.report_text.configure(state="disabled")
        self._set_report_text(self._report_placeholder())

        footer_frame = ttk.Frame(self)
        footer_frame.grid(
            row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10)
        )
        self.footer_label = ttk.Label(footer_frame, text="", anchor="center")
        self.footer_label.pack(fill=tk.X)
        self._set_footer_text()

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}", flush=True)

    def _set_report_text(self, content: str):
        self.report_text.configure(state="normal")
        self.report_text.delete("1.0", tk.END)
        self.report_text.insert("1.0", content)
        self.report_text.configure(state="disabled")

    def _report_placeholder(self) -> str:
        lang = getattr(self.controller, "current_language", "CN")
        if lang == "EN":
            return "Report Summary\n\nRun analysis to generate report.html, then key fields will be shown here."
        return "报告摘要\n\n请先进行数据分析，生成 report.html 后，这里会展示关键摘要信息。"

    def update_report_summary_from_dir(self, output_dir: Path | None):
        if not output_dir:
            self._set_report_text(self._report_placeholder())
            return

        report_json = output_dir / "report.json"
        report_html = output_dir / "report.html"

        lang = getattr(self.controller, "current_language", "CN")

        if not report_json.exists():
            if lang == "EN":
                lines = [
                    "Report Summary",
                    "",
                    f"Output: {output_dir}",
                    f"Report: {report_html if report_html.exists() else 'N/A'}",
                    "",
                    "report.json not found. Please export report again.",
                ]
            else:
                lines = [
                    "报告摘要",
                    "",
                    f"输出目录：{output_dir}",
                    f"报告文件：{report_html if report_html.exists() else 'N/A'}",
                    "",
                    "未找到 report.json。可尝试再次导出报告。",
                ]
            self._set_report_text("\n".join(lines))
            return

        try:
            import json

            info = json.loads(report_json.read_text(encoding="utf-8"))
        except Exception as e:
            if lang == "EN":
                self._set_report_text(
                    f"Report Summary\n\nFailed to read report.json:\n{str(e)}"
                )
            else:
                self._set_report_text(f"报告摘要\n\n读取 report.json 失败：\n{str(e)}")
            return

        ts = str(info.get("ts", "")).strip()
        input_path = str(info.get("input_path", "")).strip()
        lesions = info.get("lesion_analyses") or []
        surgical_plans_count = int(info.get("surgical_plans_count", 0) or 0)

        high = 0
        mid = 0
        low = 0
        diameters = []
        rads = {}
        for a in lesions:
            risk = str(a.get("risk_level", ""))
            if "Very High" in risk or "极高" in risk:
                high += 1
            elif "High" in risk or "高风险" in risk:
                high += 1
            elif "Intermediate" in risk or "中风险" in risk:
                mid += 1
            elif "Low" in risk or "低风险" in risk:
                low += 1
            d = a.get("diameter_mm", None)
            try:
                if d is not None:
                    diameters.append(float(d))
            except Exception:
                pass
            score = str(a.get("lung_rads_score", "")).strip()
            if score:
                rads[score] = rads.get(score, 0) + 1

        diameters_sorted = sorted(diameters, reverse=True)
        max_d = diameters_sorted[0] if diameters_sorted else None
        avg_d = (sum(diameters) / len(diameters)) if diameters else None

        def short(s: str, n: int):
            s = (s or "").strip().replace("\n", " ")
            return s if len(s) <= n else (s[: n - 1] + "…")

        top = sorted(
            lesions,
            key=lambda x: float(x.get("diameter_mm", 0) or 0),
            reverse=True,
        )[:5]

        if lang == "EN":
            lines = [
                "Report Summary",
                "",
                f"Output: {output_dir}",
                f"Report: {report_html if report_html.exists() else 'N/A'}",
            ]
            if ts:
                lines.append(f"Timestamp: {ts}")
            if input_path:
                lines.append(f"Input: {input_path}")
            lines += [
                "",
                f"Suspected lesions: {len(lesions)} (High: {high}, Intermediate: {mid}, Low: {low})",
            ]
            if max_d is not None:
                lines.append(f"Max diameter: {max_d:.1f} mm")
            if avg_d is not None:
                lines.append(f"Avg diameter: {avg_d:.1f} mm")
            if rads:
                parts = [f"{k}:{rads[k]}" for k in sorted(rads.keys())]
                lines.append("Lung-RADS: " + ", ".join(parts))
            lines.append(f"Surgical plans: {surgical_plans_count}")
            if top:
                lines += ["", "Top lesions (by diameter):"]
                for a in top:
                    lid = a.get("id", "")
                    try:
                        d = float(a.get("diameter_mm", 0) or 0)
                    except Exception:
                        d = 0.0
                    den = short(str(a.get("density_type", "")), 28)
                    risk = short(str(a.get("risk_level", "")), 42)
                    rec = short(str(a.get("recommendation", "")), 86)
                    lines.append(f"- #{lid} | {d:.1f} mm | {den} | {risk}")
                    if rec:
                        lines.append(f"  {rec}")
        else:
            lines = [
                "报告摘要",
                "",
                f"输出目录：{output_dir}",
                f"报告文件：{report_html if report_html.exists() else 'N/A'}",
            ]
            if ts:
                lines.append(f"时间戳：{ts}")
            if input_path:
                lines.append(f"输入：{input_path}")
            lines += [
                "",
                f"疑似病灶：{len(lesions)}（高风险：{high}，中风险：{mid}，低风险：{low}）",
            ]
            if max_d is not None:
                lines.append(f"最大直径：{max_d:.1f} mm")
            if avg_d is not None:
                lines.append(f"平均直径：{avg_d:.1f} mm")
            if rads:
                parts = [f"{k}:{rads[k]}" for k in sorted(rads.keys())]
                lines.append("Lung-RADS： " + "，".join(parts))
            lines.append(f"手术规划条目：{surgical_plans_count}")
            if top:
                lines += ["", "Top 病灶（按直径排序）："]
                for a in top:
                    lid = a.get("id", "")
                    d = float(a.get("diameter_mm", 0) or 0)
                    den = short(str(a.get("density_type", "")), 28)
                    risk = short(str(a.get("risk_level", "")), 42)
                    rec = short(str(a.get("recommendation", "")), 86)
                    lines.append(f"- #{lid} | {d:.1f} mm | {den} | {risk}")
                    if rec:
                        lines.append(f"  {rec}")

        self._set_report_text("\n".join(lines))

    def update_language(self):
        lang = self.controller.current_language

        for key, btn in self.buttons.items():
            btn.config(text=languages.get_text(key, lang))

        self.in_header_label.config(text=languages.get_text("header_input", lang))
        self.out_header_label.config(text=languages.get_text("header_output", lang))
        self.result_type_label.config(
            text=languages.get_text("label_result_type", lang)
        )
        self.slice_index_label.config(
            text=languages.get_text("label_slice_index", lang)
        )
        self.desc_label_title.config(text=languages.get_text("label_description", lang))
        self.report_frame.config(text=languages.get_text("group_report", lang))

        if self.current_result_type:
            desc_key = f"desc_{self.current_result_type}"
            desc = languages.get_text(desc_key, lang)
            if desc == desc_key:
                desc = languages.get_text("desc_default", lang)
            self.result_desc_label.config(text=desc)
        else:
            self.result_desc_label.config(text=languages.get_text("desc_default", lang))
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

    def on_import_data(self):
        path = filedialog.askopenfilename(
            title=languages.get_text(
                "title_select_file", self.controller.current_language
            ),
            filetypes=[("Numpy files", "*.npy;*.npz"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            self.log(
                languages.get_text(
                    "log_loading", self.controller.current_language
                ).format(path)
            )
            self.last_imported_path = path
            self.current_vol = load_3d_data(Path(path))

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.input_dir = APP_DIR / "input" / ts
            self.input_dir.mkdir(parents=True, exist_ok=True)

            self.result_dict = {}
            self.current_result_type = None
            self.result_type_combo["values"] = []
            self.result_type_combo.set("")

            self.current_slices = []
            self.log(
                languages.get_text(
                    "log_generating_slices", self.controller.current_language
                )
            )

            vol_disp = self.current_vol
            if vol_disp.ndim == 4:
                vol_disp = vol_disp[0]

            for idx, slice_data in slices_from_volume(vol_disp):
                s_u8 = (slice_data - slice_data.min()) / (
                    slice_data.max() - slice_data.min() + 1e-8
                )
                s_u8 = (s_u8 * 255).astype(np.uint8)

                img_path = self.input_dir / f"slice_{idx:03d}.png"
                Image.fromarray(s_u8).save(img_path)
                self.current_slices.append(img_path)

            self.slice_scale.config(to=len(self.current_slices) - 1)
            self.slice_scale.set(0)
            self.update_display(0)
            self.log(
                languages.get_text(
                    "log_loaded", self.controller.current_language
                ).format(len(self.current_slices))
            )
            self.log(
                languages.get_text(
                    "log_input_dir", self.controller.current_language
                ).format(self.input_dir)
            )

        except Exception as e:
            messagebox.showerror(
                languages.get_text("title_error", self.controller.current_language),
                languages.get_text("msg_import_fail", self.controller.current_language)
                + f": {str(e)}",
            )
            self.log(
                languages.get_text(
                    "log_error", self.controller.current_language
                ).format(str(e))
            )

    def on_analyze_data(self):
        if self.current_vol is None:
            messagebox.showwarning(
                languages.get_text("title_info", self.controller.current_language),
                languages.get_text("msg_no_data", self.controller.current_language),
            )
            return

        lang = getattr(self.controller, "current_language", "CN")
        title = "Analysis Progress" if lang == "EN" else "分析进度"
        message = "Starting..." if lang == "EN" else "正在启动..."
        dialog = ProgressRingDialog(self, title=title, message=message)
        dialog.set_indeterminate("Analyzing..." if lang == "EN" else "分析中...")
        threading.Thread(target=self._run_analysis, args=(dialog,), daemon=True).start()

    def _run_analysis(self, dialog: ProgressRingDialog):
        try:
            self.after(
                0,
                lambda: self._set_report_text(
                    "Generating report summary..."
                    if self.controller.current_language == "EN"
                    else "正在生成报告摘要..."
                ),
            )
            self.log(
                languages.get_text(
                    "log_start_analysis", self.controller.current_language
                )
            )
            self.is_analyzing = True

            if not self.last_imported_path:
                self.log(
                    languages.get_text("log_no_path", self.controller.current_language)
                )
                return

            model_script = CURRENT_DIR / "model.py"
            if not model_script.exists():
                self.log(
                    languages.get_text(
                        "log_no_script", self.controller.current_language
                    ).format(model_script)
                )
                return

            cmd = [
                sys.executable,
                str(model_script),
                "--input",
                str(self.last_imported_path),
            ]

            self.log(
                languages.get_text(
                    "log_executing", self.controller.current_language
                ).format(" ".join(cmd))
            )

            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(APP_DIR),
                env=env,
            )

            output_dir_str = None
            model_input_dir_str = None
            progress_re = re.compile(r"^PROGRESS:\s*(\d+)\s*/\s*(\d+)")
            stage_re = re.compile(r"^PROGRESS_STAGE:\s*(\w+)")
            lang = getattr(self.controller, "current_language", "CN")

            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    line = line.strip()
                    print(f"[Model] {line}", flush=True)

                    m = progress_re.match(line)
                    if m:
                        cur = int(m.group(1))
                        tot = int(m.group(2))
                        msg = (
                            f"Processing {cur}/{tot}"
                            if lang == "EN"
                            else f"正在分析 {cur}/{tot}"
                        )
                        self.after(
                            0,
                            lambda c=cur, t=tot, ms=msg: dialog.set_progress(c, t, ms),
                        )
                        continue

                    m2 = stage_re.match(line)
                    if m2:
                        stage = m2.group(1).strip().lower()
                        if stage == "report":
                            self.after(
                                0,
                                lambda: dialog.set_indeterminate(
                                    "Generating report..."
                                    if lang == "EN"
                                    else "正在生成报告..."
                                ),
                            )
                        continue

                    if "OUTPUT_DIR: " in line:
                        parts = line.split("OUTPUT_DIR: ")
                        if len(parts) > 1:
                            output_dir_str = parts[1].strip()
                    elif "处理结果已保存到: " in line:
                        parts = line.split("处理结果已保存到: ")
                        if len(parts) > 1:
                            output_dir_str = parts[1].strip()
                    elif "输入切片已保存到: " in line:
                        parts = line.split("输入切片已保存到: ")
                        if len(parts) > 1:
                            model_input_dir_str = parts[1].strip()

            rc = process.poll()
            if rc == 0:
                self.log("分析命令执行成功.")

                if model_input_dir_str:
                    model_in_dir = Path(model_input_dir_str)
                    if (
                        model_in_dir.exists()
                        and self.input_dir
                        and model_in_dir != self.input_dir
                    ):
                        self.log(f"清理冗余输入目录: {self.input_dir}")
                        try:
                            import shutil

                            if self.input_dir.exists():
                                shutil.rmtree(self.input_dir)

                            self.input_dir = model_in_dir
                            self.log(f"切换至新的输入目录: {self.input_dir}")

                            new_slices = []
                            for p in self.current_slices:
                                new_p = self.input_dir / p.name
                                new_slices.append(new_p)
                            self.current_slices = new_slices

                        except Exception as e:
                            self.log(f"清理目录失败: {str(e)}")

                if output_dir_str:
                    self.output_dir = Path(output_dir_str)
                    if self.output_dir.exists():
                        self.log(f"正在加载结果: {self.output_dir}")
                        self.load_results_from_dir(self.output_dir)
                    else:
                        self.log(f"警告: 输出目录不存在: {self.output_dir}")
                else:
                    self.log("警告: 未能从输出中捕获结果目录")
            else:
                self.log(f"分析失败, 返回码: {rc}")

        except Exception as e:
            self.log(f"分析出错: {str(e)}")
            import traceback

            traceback.print_exc()
        finally:
            self.is_analyzing = False
            self.after(0, dialog.close)

    def load_results_from_dir(self, output_dir: Path):
        self.result_dict = {}

        files = sorted(list(output_dir.glob("*.png")))

        temp_results = {}
        for p in files:
            name = p.stem
            parts = name.split("_")

            if name.startswith("proc_"):
                if len(parts) >= 3:
                    try:
                        idx = int(parts[1])
                        rtype = "_".join(parts[2:])
                        if rtype not in temp_results:
                            temp_results[rtype] = []
                        temp_results[rtype].append((idx, p))
                    except ValueError:
                        pass

            elif name.startswith("prob_"):
                if len(parts) >= 3:
                    try:
                        idx = int(parts[2])
                        rtype = parts[1]
                        rtype = f"prob_{rtype}"
                        if rtype not in temp_results:
                            temp_results[rtype] = []
                        temp_results[rtype].append((idx, p))
                    except ValueError:
                        pass

        max_idx = 0
        if temp_results:
            for rtype in temp_results:
                for idx, _ in temp_results[rtype]:
                    if idx > max_idx:
                        max_idx = idx

        num_slices = len(self.current_slices) if self.current_slices else (max_idx + 1)

        for rtype, items in temp_results.items():

            path_list = [Path("non_existent")] * num_slices

            for idx, p in items:
                if idx < num_slices:
                    path_list[idx] = p

            self.result_dict[rtype] = path_list

        self.after(
            0,
            lambda od=output_dir: (
                self._update_ui_after_analysis(
                    "overlay"
                    if "overlay" in self.result_dict
                    else list(self.result_dict.keys())[0] if self.result_dict else None
                ),
                self.update_report_summary_from_dir(od),
                self._show_toast(
                    {"CN": "数据分析完成", "EN": "Analysis completed"},
                    duration_ms=5000,
                ),
            ),
        )

    def on_visualize_3d(self):
        analyze_script = APP_DIR / "analyze3D" / "analyze_gui.py"
        if not analyze_script.exists():
            messagebox.showerror("错误", f"未找到3D可视化脚本: {analyze_script}")
            return

        cmd = [sys.executable, str(analyze_script)]

        if self.last_imported_path and self.last_imported_path.lower().endswith(".npz"):
            cmd.append(self.last_imported_path)

        try:
            subprocess.Popen(cmd)
        except Exception as e:
            messagebox.showerror("错误", f"启动3D可视化失败: {str(e)}")

    def on_unet_analysis(self):
        if not self.input_dir:
            messagebox.showwarning("提示", "请先导入数据")
            return

        lang = getattr(self.controller, "current_language", "CN")
        title = "Traditional U-Net" if lang == "EN" else "传统U-Net分析"
        message = "Preparing..." if lang == "EN" else "正在准备..."
        dialog = ProgressRingDialog(self, title=title, message=message)
        threading.Thread(target=self._run_unet, args=(dialog,), daemon=True).start()

    def _run_unet(self, dialog: ProgressRingDialog):
        try:
            self.log("开始传统U-Net分析...")
            try:
                from ACX_UNET.unet import Unet
            except ImportError:
                sys.path.append(str(APP_DIR / "ACX-UNET"))
                from unet import Unet

            unet = Unet()

            if not self.output_dir:
                ts = self.input_dir.name
                self.output_dir = APP_DIR / "output" / ts
                self.output_dir.mkdir(parents=True, exist_ok=True)

            result_list = []
            img_files = sorted(list(self.input_dir.glob("*.png")))
            total = len(img_files)
            lang = getattr(self.controller, "current_language", "CN")
            if total > 0:
                self.after(
                    0,
                    lambda: dialog.set_progress(
                        0,
                        total,
                        (
                            "Processing 0/{}".format(total)
                            if lang == "EN"
                            else "正在分析 0/{}".format(total)
                        ),
                    ),
                )

            for i, img_path in enumerate(img_files, start=1):
                image = Image.open(img_path)
                r_image = unet.detect_image(image)

                out_name = img_path.name.replace("slice", "unet")
                out_path = self.output_dir / out_name
                r_image.save(out_path)
                result_list.append(out_path)
                self.after(
                    0,
                    lambda c=i, t=total: dialog.set_progress(
                        c,
                        t,
                        f"Processing {c}/{t}" if lang == "EN" else f"正在分析 {c}/{t}",
                    ),
                )

            self.result_dict["ACX-UNET"] = result_list

            self.log("传统U-Net分析完成.")
            self.after(
                0,
                lambda: (
                    self._update_ui_after_analysis("ACX-UNET"),
                    self._show_toast(
                        {"CN": "数据分析完成", "EN": "Analysis completed"},
                        duration_ms=5000,
                    ),
                ),
            )

        except Exception as e:
            self.log(f"U-Net分析出错: {str(e)}")
            import traceback

            traceback.print_exc()
        finally:
            self.after(0, dialog.close)

    def _update_ui_after_analysis(self, initial_type):
        if self.result_dict:
            types = list(self.result_dict.keys())
            types = [t for t in types if not t.endswith("_anno")]
            self.result_type_combo["values"] = types

            if initial_type and initial_type in types:
                self.result_type_combo.set(initial_type)
                self.current_result_type = initial_type

                desc_key = f"desc_{initial_type}"
                desc = languages.get_text(desc_key, self.controller.current_language)
                if desc == desc_key:
                    desc_key_lower = f"desc_{initial_type.lower().replace('-', '_')}"
                    desc = languages.get_text(
                        desc_key_lower, self.controller.current_language
                    )
                    if desc == desc_key_lower:
                        desc = languages.get_text(
                            "desc_default", self.controller.current_language
                        )
                self.result_desc_label.config(text=desc)
            elif types:
                self.result_type_combo.set(types[0])
                self.current_result_type = types[0]

                desc_key = f"desc_{types[0]}"
                desc = languages.get_text(desc_key, self.controller.current_language)
                if desc == desc_key:
                    desc_key_lower = f"desc_{types[0].lower().replace('-', '_')}"
                    desc = languages.get_text(
                        desc_key_lower, self.controller.current_language
                    )
                    if desc == desc_key_lower:
                        desc = languages.get_text(
                            "desc_default", self.controller.current_language
                        )
                self.result_desc_label.config(text=desc)

            self.update_display(self.current_slice_idx)
            self.log(f"Analysis completed. Loaded {len(types)} result types.")

    def on_result_type_change(self, event):
        self.current_result_type = self.result_type_combo.get()
        if self.current_result_type:
            desc_key = f"desc_{self.current_result_type}"
            desc = languages.get_text(desc_key, self.controller.current_language)

            if desc == desc_key:
                desc_key_lower = (
                    f"desc_{self.current_result_type.lower().replace('-', '_')}"
                )
                desc = languages.get_text(
                    desc_key_lower, self.controller.current_language
                )

                if desc == desc_key_lower:
                    desc = languages.get_text(
                        "desc_default", self.controller.current_language
                    )

            self.result_desc_label.config(text=desc)
        self.update_display(self.current_slice_idx)

    def on_export_report(self):
        if not self.output_dir or self.current_vol is None:
            messagebox.showwarning("提示", "请先进行数据分析")
            return

        lang = getattr(self.controller, "current_language", "CN")
        title = "Export Report" if lang == "EN" else "导出报告"
        duration_ms = 2000
        state = {
            "popup_done": False,
            "report_done": False,
            "toast_shown": False,
            "report_path": None,
            "failed": False,
        }
        try:
            self._typing_dots_dialog = TypingDotsDialog(
                self,
                title=title,
                caption="Generating Reports",
                duration_ms=duration_ms,
                on_close=lambda: (
                    setattr(self, "_typing_dots_dialog", None),
                    state.__setitem__("popup_done", True),
                    self._maybe_show_report_toast_after_export(state),
                ),
            )
        except Exception:
            self._typing_dots_dialog = None
            state["popup_done"] = True
            self._maybe_show_report_toast_after_export(state)
        threading.Thread(
            target=self._export_report_worker, args=(state,), daemon=True
        ).start()

    def _maybe_show_report_toast_after_export(self, state: dict):
        if state.get("toast_shown"):
            return
        if state.get("failed"):
            return
        if not state.get("popup_done"):
            return
        if not state.get("report_done"):
            return
        report_path = state.get("report_path")
        if not report_path:
            return
        state["toast_shown"] = True

        lang = getattr(self.controller, "current_language", "CN")
        message = {"CN": "报告已生成", "EN": "Report generated"}
        button_text = {"CN": "打开报告", "EN": "Open report"}

        def _open_report():
            import webbrowser

            webbrowser.open(str(report_path))

        self._show_toast(
            message=message, button_text=button_text, on_button=_open_report
        )

    def _export_report_worker(self, state: dict):
        try:
            self.log("正在生成报告...")

            contrast = "slice"
            robust_low = 1.0
            robust_high = 99.0
            window_center = None
            window_width = None
            fg_classes = "1"
            overlay_alpha = 0.4
            prob_threshold = 0.5

            recon_mask = None
            recon_probs = None

            target_key = "mask"
            if target_key not in self.result_dict:
                target_key = "binary"

            if target_key not in self.result_dict and self.current_result_type:
                target_key = self.current_result_type

            if target_key in self.result_dict:
                current_results = self.result_dict[target_key]
                D, H, W = (
                    self.current_vol.shape
                    if self.current_vol.ndim == 3
                    else self.current_vol.shape[1:]
                )
                if self.current_vol.ndim == 4:
                    D, H, W = self.current_vol.shape[1:]

                recon_mask = np.zeros((D, H, W), dtype=np.uint8)
                for i, path in enumerate(current_results):
                    if i < D and path.exists():
                        try:
                            img = Image.open(path)
                            m = np.array(img.convert("L"))
                            recon_mask[i] = (m > 127).astype(np.uint8)
                        except Exception:
                            pass

            ts = self.output_dir.name
            weights_path = CURRENT_DIR / "best_model.pth"
            model_info = {"type": "pytorch" if weights_path.exists() else "none"}

            lesion_data = None
            lesion_data_path = self.output_dir / "lesion_data.json"
            if lesion_data_path.exists():
                try:
                    import json

                    with open(lesion_data_path, "r", encoding="utf-8") as f:
                        lesion_data = json.load(f)
                except Exception:
                    pass

            generate_report(
                ts=ts,
                vol=(
                    self.current_vol
                    if self.current_vol.ndim == 3
                    else self.current_vol[0]
                ),
                recon_mask=recon_mask,
                recon_probs=None,
                input_dir=self.input_dir,
                output_dir=self.output_dir,
                model_info=model_info,
                contrast=contrast,
                robust_low=robust_low,
                robust_high=robust_high,
                window_center=window_center,
                window_width=window_width,
                fg_classes=fg_classes,
                overlay_alpha=overlay_alpha,
                prob_threshold=prob_threshold,
                input_path=Path("loaded_from_gui"),
                weights_path=weights_path,
                lesion_data=lesion_data,
            )

            self.log(f"报告生成成功: {self.output_dir / 'report.html'}")
            self.after(0, lambda: self.update_report_summary_from_dir(self.output_dir))
            state["report_path"] = self.output_dir / "report.html"
            state["report_done"] = True
            self.after(0, lambda: self._maybe_show_report_toast_after_export(state))

        except Exception as e:
            self.log(f"导出报告失败: {str(e)}")
            import traceback

            traceback.print_exc()
            state["failed"] = True

    def on_slice_change(self, val):
        idx = int(float(val))
        self.current_slice_idx = idx
        self.update_display(idx)

    def update_display(self, idx):
        if not self.current_slices:
            return

        idx = max(0, min(idx, len(self.current_slices) - 1))
        self.slice_label.config(text=f"{idx+1}/{len(self.current_slices)}")

        input_path = self.current_slices[idx]
        if input_path.exists():
            img = Image.open(input_path)
            cw = self.input_canvas.winfo_width()
            ch = self.input_canvas.winfo_height()
            if cw > 1 and ch > 1:
                w, h = img.size
                ratio = min(cw / w, ch / h)
                new_w, new_h = int(w * ratio), int(h * ratio)
                if new_w > 0 and new_h > 0:
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            self.input_img_tk = ImageTk.PhotoImage(img)
            self.input_canvas.delete("all")
            self.input_canvas.create_image(cw // 2, ch // 2, image=self.input_img_tk)

        if self.current_result_type and self.current_result_type in self.result_dict:
            rtype = self.current_result_type

            results = self.result_dict[rtype]
            if idx < len(results):
                out_path = results[idx]
                if out_path.exists():
                    img = Image.open(out_path)
                    cw = self.output_canvas.winfo_width()
                    ch = self.output_canvas.winfo_height()
                    if cw > 1 and ch > 1:
                        w, h = img.size
                        ratio = min(cw / w, ch / h)
                        new_w, new_h = int(w * ratio), int(h * ratio)
                        if new_w > 0 and new_h > 0:
                            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                    self.output_img_tk = ImageTk.PhotoImage(img)
                    self.output_canvas.delete("all")
                    self.output_canvas.create_image(
                        cw // 2, ch // 2, image=self.output_img_tk
                    )
        else:
            self.output_canvas.delete("all")


if __name__ == "__main__":

    class MockController:
        def __init__(self):
            self.current_language = "CN"

    root = tk.Tk()
    root.geometry("1200x800")
    style = ttk.Style()
    style.theme_use("clam")

    app = ModelInterface(root, MockController())
    app.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
