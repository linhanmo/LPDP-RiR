import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
APP_DIR = CURRENT_DIR.parent
PROJECT_ROOT = APP_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.append(str(APP_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from application.gui import styles
from application.gui import languages


class Homepage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._text_targets = []
        self._images = []
        self.create_widgets()
        self.update_language()

    def create_widgets(self):
        self._colors = {
            "bg": "#f0f7ff",
            "text": "#2c3e50",
            "muted": "#5a6b7a",
            "primary": "#2980b9",
            "primary_hover": "#1f6391",
            "card": "#ffffff",
            "border": "#d9e6f2",
            "header_bg": "#f0f7ff",
        }

        self.configure(bg=self._colors["bg"])

        self._canvas = tk.Canvas(
            self,
            bg=self._colors["bg"],
            highlightthickness=0,
            bd=0,
        )
        self._scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self._canvas.yview
        )
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._content = tk.Frame(self._canvas, bg=self._colors["bg"])
        self._content_window = self._canvas.create_window(
            (0, 0), window=self._content, anchor="nw"
        )

        self._content.bind("<Configure>", self._on_content_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        self._build_hero(self._content)
        self._build_key_metrics(self._content)
        self._build_advantages(self._content)
        self._build_core_capabilities(self._content)
        self._build_footer(self._content)

    def _on_content_configure(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfigure(self._content_window, width=event.width)

    def _on_mouse_wheel(self, event):
        try:
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    def on_mousewheel(self, event):
        self._on_mouse_wheel(event)

    def _t(self, key):
        lang = getattr(self.controller, "current_language", "CN") or "CN"
        if key in self._texts:
            return self._texts.get(key, {}).get(lang, key)
        return languages.get_text(key, lang)

    def _font(self, kind):
        lang = getattr(self.controller, "current_language", "CN") or "CN"
        family = styles.FONT_FAMILY_CN if lang == "CN" else styles.FONT_FAMILY_EN
        if kind == "main_title":
            return (family, 34, "bold")
        if kind == "sub_title":
            return (family, 22)
        if kind == "section_title":
            return (family, 20, "bold")
        if kind == "section_subtitle":
            return (family, 12)
        if kind == "metric_value":
            return (family, 24, "bold")
        if kind == "card_title":
            return (family, 12, "bold")
        if kind == "body":
            return (family, 11)
        if kind == "button":
            return (family, 11, "bold")
        if kind == "table_header":
            return (family, 11, "bold")
        return (family, 11)

    def _register_text(self, widget, key):
        self._text_targets.append((widget, key))

    def _build_nav_like_header(self, parent):
        header = tk.Frame(parent, bg=self._colors["card"])
        header.pack(fill=tk.X, padx=20, pady=(16, 0))

        left = tk.Frame(header, bg=self._colors["card"])
        left.pack(side=tk.LEFT, padx=(20, 0), pady=16)

        logo_path = APP_DIR / "logo" / "logo.png"
        if logo_path.exists():
            try:
                self._logo_img = tk.PhotoImage(file=str(logo_path))
                self._images.append(self._logo_img)
                logo = tk.Label(
                    left,
                    image=self._logo_img,
                    bg=self._colors["card"],
                )
                logo.pack(side=tk.LEFT)
            except Exception:
                pass

        self._logo_text = tk.Label(
            left,
            text="LPDP-RiR Intelligent Medical Platform",
            bg=self._colors["card"],
            fg=self._colors["text"],
            font=self._font("card_title"),
        )
        self._logo_text.pack(side=tk.LEFT, padx=(10, 0))
        self._register_text(self._logo_text, "logo_text")

        right = tk.Frame(header, bg=self._colors["card"])
        right.pack(side=tk.RIGHT, padx=(0, 20), pady=16)

        btns = [
            ("nav_home", "Homepage"),
            ("nav_intro", "Introduction"),
            ("nav_model", "ModelInterface"),
            ("nav_history", "History"),
        ]

        self._nav_buttons = []
        for key, page_key in btns:
            b = tk.Button(
                right,
                text="",
                font=self._font("button"),
                bg=self._colors["primary"],
                fg="white",
                activebackground=self._colors["primary_hover"],
                activeforeground="white",
                bd=0,
                padx=14,
                pady=8,
                cursor="hand2",
                command=lambda k=page_key: self.controller.show_frame(k),
            )
            b.pack(side=tk.LEFT, padx=6)
            self._register_text(b, key)
            self._nav_buttons.append(b)

    def _build_hero(self, parent):
        self._texts = {
            "logo_text": {
                "CN": "LPDP-RiR 智能医疗平台",
                "EN": "LPDP-RiR Intelligent Medical Platform",
            },
            "hero_title": {
                "CN": "欢迎来到 LPDP-RiR 智能医疗平台",
                "EN": "Welcome to LPDP-RiR Intelligent Medical Platform",
            },
            "hero_subtitle": {
                "CN": "面向边缘设备的行业领先平台，提供影像处理、分析、辅助诊断与治疗一体化能力",
                "EN": "An industry-leading platform for image processing, analysis, auxiliary diagnosis and treatment, tailored for edge devices",
            },
            "cta_quick_start": {"CN": "快速开始", "EN": "Quick Start"},
            "cta_request_trial": {"CN": "高级功能", "EN": "Advanced Functions"},
            "cta_download_preview": {"CN": "账户与帮助", "EN": "Account & Get Help"},
            "cta_paper_link": {"CN": "论文链接", "EN": "Paper Link"},
            "section_key_metrics_title": {"CN": "关键指标", "EN": "Key Metrics"},
            "section_key_metrics_subtitle": {
                "CN": "基于多中心验证、部署测试与工作流对比得到的指标概览。",
                "EN": "Benchmarks derived from multi-center validation, deployment tests, and workflow comparisons.",
            },
            "metric_dice_label": {
                "CN": "Dice 相似系数（肺结节分割）",
                "EN": "Dice Similarity (Lung Nodule Segmentation)",
            },
            "metric_dice_note": {
                "CN": "采用 INT8 量化 + 20% 频域剪枝。",
                "EN": "With INT8 quantization + 20% frequency-domain pruning.",
            },
            "metric_hd95_label": {"CN": "HD95", "EN": "HD95"},
            "metric_hd95_note": {
                "CN": "核心分割基准上的 95% Hausdorff 距离。",
                "EN": "95% Hausdorff distance on core segmentation benchmarks.",
            },
            "metric_time_label": {
                "CN": "单例端到端耗时",
                "EN": "Single-Case End-to-End Time",
            },
            "metric_time_note": {
                "CN": "胸部 CT 工作流对比指标。",
                "EN": "Workflow comparison metric for chest CT processing.",
            },
            "metric_pacs_label": {
                "CN": "PACS 厂商集成数",
                "EN": "PACS Vendor Integrations",
            },
            "metric_pacs_note": {
                "CN": "支持 DICOM 核心服务 + HL7 v2 / HL7 FHIR。",
                "EN": "DICOM core services + HL7 v2 / HL7 FHIR support.",
            },
            "section_workflow_title": {"CN": "工作流效率", "EN": "Workflow Efficiency"},
            "section_workflow_subtitle": {
                "CN": "跨临床任务的运营影响对比视图。",
                "EN": "A compact view of operational impact across clinical tasks.",
            },
            "wf_col_metric": {"CN": "指标", "EN": "Metric"},
            "wf_col_manual": {"CN": "人工", "EN": "Manual"},
            "wf_col_typical_ai": {"CN": "典型 AI", "EN": "Typical AI"},
            "wf_col_lpdp": {"CN": "LPDP-RiR", "EN": "LPDP-RiR"},
            "wf_row1": {
                "CN": "胸部 CT 单例端到端处理时间",
                "EN": "Chest CT end-to-end processing time (single case)",
            },
            "wf_row2": {
                "CN": "100 例批处理总耗时",
                "EN": "100-case batch processing total time",
            },
            "wf_row3": {
                "CN": "基层肺部疾病误诊率",
                "EN": "Primary-care lung disease misdiagnosis rate",
            },
            "wf_row4": {
                "CN": "单例手术路径规划时间",
                "EN": "Surgical path planning time (single case)",
            },
            "wf_row5": {
                "CN": "AR 术中导航静态定位误差",
                "EN": "AR intraoperative navigation static positioning error",
            },
            "section_adv_title": {"CN": "优势", "EN": "Advantages"},
            "section_adv_subtitle": {
                "CN": "强泛化、低硬件要求与快速院内集成。",
                "EN": "Robust generalization, low hardware requirements, and rapid hospital integration.",
            },
            "adv_why_title": {"CN": "为何选择 LPDP-RiR", "EN": "Why LPDP-RiR"},
            "adv_why_1": {
                "CN": "多中心泛化能力强，Dice 相对下降 < 1.2%。",
                "EN": "Multi-center generalization with <1.2% Dice relative drop.",
            },
            "adv_why_2": {
                "CN": "1000 例连续推理稳定（±0.2% 波动）。",
                "EN": "Stable inference over 1000 consecutive cases (±0.2% variation).",
            },
            "adv_why_3": {
                "CN": "全面支持 ARM/x86，适配树莓派等轻量场景。",
                "EN": "Full ARM/x86 support, including lightweight Raspberry Pi scenarios.",
            },
            "adv_design_title": {"CN": "高级能力设计", "EN": "Advanced by Design"},
            "adv_design_1": {
                "CN": "支持 DICOM 核心服务与 HL7 FHIR，适配现代医院工作流。",
                "EN": "Full DICOM core services and HL7 FHIR support for modern hospital workflows.",
            },
            "adv_design_2": {
                "CN": "快速集成：每家医院 3–7 天（SDK / DICOM 代理，零核心接口改造）。",
                "EN": "Fast integration: 3–7 days per hospital (SDK / DICOM proxy, zero core-interface refactor).",
            },
            "adv_design_3": {
                "CN": "安全部署：AES-256 与国密级加密方案可选。",
                "EN": "Security-forward deployment with AES-256 and SM-grade encryption options.",
            },
            "section_core_title": {"CN": "核心能力", "EN": "Core Capabilities"},
            "section_core_subtitle": {
                "CN": "从平台视角展示首页核心能力。",
                "EN": "A platform view of the most visible capabilities on the cover page.",
            },
            "feature_edge_title": {"CN": "边缘推理", "EN": "Edge Inference"},
            "feature_edge_desc": {
                "CN": "在边缘设备上实现实时影像分析与辅助诊断。",
                "EN": "Real-time image analysis and assisted diagnosis on edge devices.",
            },
            "feature_workflow_title": {
                "CN": "一体化工作流",
                "EN": "Integrated Workflow",
            },
            "feature_workflow_desc": {
                "CN": "统一的影像处理、分析、标注与结果导出能力。",
                "EN": "Unified image processing, analysis, annotation, and result export.",
            },
            "feature_security_title": {
                "CN": "安全与合规",
                "EN": "Security & Compliance",
            },
            "feature_security_desc": {
                "CN": "隐私保护、访问控制与安全的数据传输。",
                "EN": "Privacy protection, access control, and secure data transfer.",
            },
            "footer": {
                "CN": "© LPDP-RiR 智能医疗平台",
                "EN": "© LPDP-RiR Intelligent Medical Platform",
            },
            "cta_msg": {
                "CN": "该功能为演示入口，可通过上方导航进入对应模块。",
                "EN": "This is a demo entry. Use the top navigation to open the corresponding module.",
            },
        }

        if not (self.controller and hasattr(self.controller, "navbar")):
            self._build_nav_like_header(parent)

        hero = tk.Frame(parent, bg=self._colors["bg"])
        hero.pack(fill=tk.X, padx=20, pady=(10, 8))

        hero_inner = tk.Frame(hero, bg=self._colors["bg"])
        hero_inner.pack(fill=tk.X, padx=20, pady=20)

        self._hero_title = tk.Label(
            hero_inner,
            text="",
            bg=self._colors["bg"],
            fg=self._colors["text"],
            font=self._font("main_title"),
            justify=tk.CENTER,
            wraplength=1100,
        )
        self._hero_title.pack(fill=tk.X, pady=(6, 10))
        self._register_text(self._hero_title, "hero_title")

        self._hero_subtitle = tk.Label(
            hero_inner,
            text="",
            bg=self._colors["bg"],
            fg=self._colors["muted"],
            font=self._font("sub_title"),
            justify=tk.CENTER,
            wraplength=1100,
        )
        self._hero_subtitle.pack(fill=tk.X, pady=(0, 16))
        self._register_text(self._hero_subtitle, "hero_subtitle")

        cta = tk.Frame(hero_inner, bg=self._colors["bg"])
        cta.pack(pady=(4, 8))

        self._cta_quick = tk.Button(
            cta,
            text="",
            font=self._font("button"),
            bg=self._colors["primary"],
            fg="white",
            activebackground=self._colors["primary_hover"],
            activeforeground="white",
            bd=0,
            padx=18,
            pady=10,
            cursor="hand2",
            command=lambda: self.controller.show_frame("ModelInterface"),
        )
        self._cta_quick.pack(side=tk.LEFT, padx=8)
        self._register_text(self._cta_quick, "cta_quick_start")

        def make_secondary(text_key):
            b = tk.Button(
                cta,
                text="",
                font=self._font("button"),
                bg=self._colors["card"],
                fg=self._colors["primary"],
                activebackground=self._colors["header_bg"],
                activeforeground=self._colors["primary"],
                bd=1,
                relief=tk.SOLID,
                highlightthickness=0,
                padx=18,
                pady=10,
                cursor="hand2",
                command=self._cta_info,
            )
            self._register_text(b, text_key)
            return b

        self._cta_trial = make_secondary("cta_request_trial")
        self._cta_trial.pack(side=tk.LEFT, padx=8)
        self._cta_download = make_secondary("cta_download_preview")
        self._cta_download.pack(side=tk.LEFT, padx=8)
        self._cta_paper = make_secondary("cta_paper_link")
        self._cta_paper.pack(side=tk.LEFT, padx=8)

    def _cta_info(self):
        title = languages.get_text(
            "title_info", getattr(self.controller, "current_language", "CN") or "CN"
        )
        messagebox.showinfo(title, self._t("cta_msg"))

    def _section(self, parent, title_key, subtitle_key):
        section = tk.Frame(parent, bg=self._colors["bg"])
        section.pack(fill=tk.X, padx=20, pady=(10, 0))

        header = tk.Frame(section, bg=self._colors["bg"])
        header.pack(fill=tk.X, padx=20, pady=(10, 6))

        title = tk.Label(
            header,
            text="",
            bg=self._colors["bg"],
            fg=self._colors["text"],
            font=self._font("section_title"),
            anchor="w",
        )
        title.pack(fill=tk.X)
        self._register_text(title, title_key)

        subtitle = tk.Label(
            header,
            text="",
            bg=self._colors["bg"],
            fg=self._colors["muted"],
            font=self._font("section_subtitle"),
            anchor="w",
            justify=tk.LEFT,
            wraplength=1100,
        )
        subtitle.pack(fill=tk.X, pady=(4, 0))
        self._register_text(subtitle, subtitle_key)

        body = tk.Frame(section, bg=self._colors["bg"])
        body.pack(fill=tk.X, padx=20, pady=(6, 10))
        return body

    def _card(self, parent):
        c = tk.Frame(
            parent,
            bg=self._colors["card"],
            highlightbackground=self._colors["border"],
            highlightthickness=1,
            bd=0,
        )
        return c

    def _build_key_metrics(self, parent):
        body = self._section(
            parent, "section_key_metrics_title", "section_key_metrics_subtitle"
        )

        grid = tk.Frame(body, bg=self._colors["bg"])
        grid.pack(fill=tk.X)

        cards = [
            ("0.9792", "metric_dice_label", "metric_dice_note"),
            ("1.65mm", "metric_hd95_label", "metric_hd95_note"),
            ("0.04s", "metric_time_label", "metric_time_note"),
            ("12", "metric_pacs_label", "metric_pacs_note"),
        ]

        self._metric_cards = []
        for i, (value, label_key, note_key) in enumerate(cards):
            card = self._card(grid)
            r, c = divmod(i, 2)
            card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")
            grid.grid_columnconfigure(c, weight=1, uniform="metric")

            v = tk.Label(
                card,
                text=value,
                bg=self._colors["card"],
                fg=self._colors["primary"],
                font=self._font("metric_value"),
                anchor="w",
            )
            v.pack(fill=tk.X, padx=16, pady=(14, 6))

            lbl = tk.Label(
                card,
                text="",
                bg=self._colors["card"],
                fg=self._colors["text"],
                font=self._font("card_title"),
                anchor="w",
                wraplength=520,
                justify=tk.LEFT,
            )
            lbl.pack(fill=tk.X, padx=16, pady=(0, 4))
            self._register_text(lbl, label_key)

            note = tk.Label(
                card,
                text="",
                bg=self._colors["card"],
                fg="#34495e",
                font=self._font("body"),
                anchor="w",
                wraplength=520,
                justify=tk.LEFT,
            )
            note.pack(fill=tk.X, padx=16, pady=(0, 14))
            self._register_text(note, note_key)

            self._metric_cards.append(card)

    def _build_workflow_table(self, parent):
        body = self._section(
            parent, "section_workflow_title", "section_workflow_subtitle"
        )

        wrap = tk.Frame(
            body,
            bg=self._colors["card"],
            highlightbackground=self._colors["border"],
            highlightthickness=1,
            bd=0,
        )
        wrap.pack(fill=tk.X, padx=2, pady=2)

        table = tk.Frame(wrap, bg=self._colors["card"])
        table.pack(fill=tk.X, padx=2, pady=2)

        headers = ["wf_col_metric", "wf_col_manual", "wf_col_typical_ai", "wf_col_lpdp"]
        for col, key in enumerate(headers):
            cell = tk.Label(
                table,
                text="",
                bg=self._colors["header_bg"],
                fg=self._colors["text"],
                font=self._font("table_header"),
                padx=12,
                pady=10,
                anchor="w",
            )
            cell.grid(row=0, column=col, sticky="nsew")
            self._register_text(cell, key)
            table.grid_columnconfigure(col, weight=1)

        rows = [
            ("wf_row1", "180–300s", "15–30s", "0.04s"),
            ("wf_row2", "50h", "50min", "<5s"),
            ("wf_row3", "20%–30%", "8%–12%", "<5%"),
            ("wf_row4", "30–60min", "5–10min", "<10s"),
            ("wf_row5", "-", "3–5mm", "<1mm"),
        ]

        for r, (metric_key, manual, typical, lpdp) in enumerate(rows, start=1):
            metric = tk.Label(
                table,
                text="",
                bg=self._colors["card"],
                fg=self._colors["text"],
                font=self._font("body"),
                padx=12,
                pady=10,
                anchor="w",
                justify=tk.LEFT,
                wraplength=520,
            )
            metric.grid(row=r, column=0, sticky="nsew")
            self._register_text(metric, metric_key)

            for c, txt in enumerate([manual, typical, lpdp], start=1):
                cell = tk.Label(
                    table,
                    text=txt,
                    bg=self._colors["card"],
                    fg=self._colors["text"],
                    font=self._font("body"),
                    padx=12,
                    pady=10,
                    anchor="w",
                )
                cell.grid(row=r, column=c, sticky="nsew")

            sep = tk.Frame(table, bg=self._colors["border"], height=1)
            sep.grid(row=r, column=0, columnspan=4, sticky="sew")

    def _build_advantages(self, parent):
        body = self._section(parent, "section_adv_title", "section_adv_subtitle")

        grid = tk.Frame(body, bg=self._colors["bg"])
        grid.pack(fill=tk.X)

        left = self._card(grid)
        right = self._card(grid)
        left.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        right.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        grid.grid_columnconfigure(0, weight=1, uniform="adv")
        grid.grid_columnconfigure(1, weight=1, uniform="adv")

        t1 = tk.Label(
            left,
            text="",
            bg=self._colors["card"],
            fg=self._colors["text"],
            font=self._font("card_title"),
            anchor="w",
        )
        t1.pack(fill=tk.X, padx=16, pady=(14, 10))
        self._register_text(t1, "adv_why_title")

        self._adv_left_items = []
        for key in ["adv_why_1", "adv_why_2", "adv_why_3"]:
            row = tk.Frame(left, bg=self._colors["card"])
            row.pack(fill=tk.X, padx=16, pady=4)
            dot = tk.Label(
                row,
                text="•",
                bg=self._colors["card"],
                fg=self._colors["primary"],
                font=self._font("body"),
            )
            dot.pack(side=tk.LEFT, padx=(0, 8))
            lbl = tk.Label(
                row,
                text="",
                bg=self._colors["card"],
                fg="#34495e",
                font=self._font("body"),
                anchor="w",
                justify=tk.LEFT,
                wraplength=520,
            )
            lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._register_text(lbl, key)
            self._adv_left_items.append(lbl)

        t2 = tk.Label(
            right,
            text="",
            bg=self._colors["card"],
            fg=self._colors["text"],
            font=self._font("card_title"),
            anchor="w",
        )
        t2.pack(fill=tk.X, padx=16, pady=(14, 10))
        self._register_text(t2, "adv_design_title")

        self._adv_right_items = []
        for key in ["adv_design_1", "adv_design_2", "adv_design_3"]:
            row = tk.Frame(right, bg=self._colors["card"])
            row.pack(fill=tk.X, padx=16, pady=4)
            dot = tk.Label(
                row,
                text="•",
                bg=self._colors["card"],
                fg=self._colors["primary"],
                font=self._font("body"),
            )
            dot.pack(side=tk.LEFT, padx=(0, 8))
            lbl = tk.Label(
                row,
                text="",
                bg=self._colors["card"],
                fg="#34495e",
                font=self._font("body"),
                anchor="w",
                justify=tk.LEFT,
                wraplength=520,
            )
            lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._register_text(lbl, key)
            self._adv_right_items.append(lbl)

        tk.Frame(left, bg=self._colors["card"], height=8).pack(fill=tk.X)
        tk.Frame(right, bg=self._colors["card"], height=8).pack(fill=tk.X)

    def _build_core_capabilities(self, parent):
        body = self._section(parent, "section_core_title", "section_core_subtitle")

        grid = tk.Frame(body, bg=self._colors["bg"])
        grid.pack(fill=tk.X)

        cards = [
            ("feature_edge_title", "feature_edge_desc"),
            ("feature_workflow_title", "feature_workflow_desc"),
            ("feature_security_title", "feature_security_desc"),
        ]

        for i, (tkey, dkey) in enumerate(cards):
            card = self._card(grid)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            grid.grid_columnconfigure(i, weight=1, uniform="feat")

            title = tk.Label(
                card,
                text="",
                bg=self._colors["card"],
                fg=self._colors["text"],
                font=self._font("card_title"),
                anchor="w",
            )
            title.pack(fill=tk.X, padx=16, pady=(14, 6))
            self._register_text(title, tkey)

            desc = tk.Label(
                card,
                text="",
                bg=self._colors["card"],
                fg="#34495e",
                font=self._font("body"),
                anchor="w",
                justify=tk.LEFT,
                wraplength=340,
            )
            desc.pack(fill=tk.X, padx=16, pady=(0, 14))
            self._register_text(desc, dkey)

    def _build_footer(self, parent):
        footer = tk.Frame(parent, bg=self._colors["bg"])
        footer.pack(fill=tk.X, padx=20, pady=(10, 16))

        self._footer_label = tk.Label(
            footer,
            text="",
            bg=self._colors["bg"],
            fg="#7f8c8d",
            font=self._font("section_subtitle"),
            anchor="center",
        )
        self._footer_label.pack(fill=tk.X, pady=8)
        self._register_text(self._footer_label, "footer")

    def update_language(self):
        for widget, key in self._text_targets:
            try:
                widget.config(text=self._t(key))
            except Exception:
                pass

        try:
            self._hero_title.config(font=self._font("main_title"))
            self._hero_subtitle.config(font=self._font("sub_title"))
            self._cta_quick.config(font=self._font("button"))
            self._cta_trial.config(font=self._font("button"))
            self._cta_download.config(font=self._font("button"))
            self._cta_paper.config(font=self._font("button"))
        except Exception:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1280x960")
    app = Homepage(root, None)
    app.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
