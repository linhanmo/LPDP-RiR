import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from pathlib import Path
import sys
import re

CURRENT_DIR = Path(__file__).resolve().parent
APP_DIR = CURRENT_DIR.parent
PROJECT_ROOT = APP_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.append(str(APP_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from application.gui import styles
from application.gui import languages


_EMBEDDED_BENCHMARK_MD = """## 表1:核心分割性能硬指标对比表

|量化指标|传统 3D UNet (FP32)|行业金标准 nnUNet (FP32)|主流 Transformer 类 Swin UNETR (FP32)|项目基线 Zig-RiR (FP32)|本项目 LPDP-RiR (INT8+20% 频域剪枝 )|
|---|---|---|---|---|---|
|Dice 相似系数|0.9235|0.9781|0.9517|0.9818|0.9792|
|95% 豪斯多夫距离 HD95 (mm)|8.72|1.83|2.15|1.62|1.65|
|交并比 IoU|0.8582|0.9572|0.9078|0.9645|0.9594|
|病灶精准度|0.8912|0.9683|0.9325|0.9762|0.9741|
|病灶召回率|0.8745|0.9710|0.9288|0.9803|0.9785|
|≤5mm 微小结节识别率|62.3%|89.7%|78.4%|91.2%|90.5%|
|误分割率|3.27%|0.82%|1.35%|0.31%|0.28%|

## 表2:轻量化效果核心数据对比表

|量化指标|3D UNet (INT8 通用量化 )|Swin UNETR (INT8 通用量化 )|Zig-RiR (INT8 通用量化 )|本项目 LPDP-RiR (INT8 量化 +20% 频域剪枝 )|
|---|---|---|---|---|
|模型参数量 (M)|5.9|6.825|10.6|9.6|
|参数量压缩比|4 倍|4 倍|4 倍|4.42 倍|
|单例推理延迟 (s)|0.110|0.092|0.058|0.040|
|推理延迟降低率|67.8%|67.8%|53.6%|68.0%|
|峰值显存占用 (GB)|2.18|2.59|3.58|3.58|
|显存占用压缩比|4 倍|4 倍|4.32 倍|4.32 倍|
|相对 FP32 模型 Dice 损失|1.53%|1.26%|0.09%|0.265%|
|最小部署包体积 (MB)|450|520|300|200|
|离线部署支持|不支持|不支持|支持|支持|

## 表3:临床场景效率数据对比表

|量化指标|放射科医生人工阅片|传统AI辅助方案|本项目LPDP-RiR 技术|
|---|---|---|---|
|单例胸部CT影像全流程处理时长|180-300s|15-30s|0.04s|
|单医生日均最大阅片量(例)|200|350|500+|
|100例批量影像处理总时长|50h|50min|<5s|
|基层医疗机构肺部疾病误诊率|20%-30%|8%-12%|<5%|
|单例手术路径规划耗时|30-60min|5-10min|<10s|
|AR术中导航静态定位误差(mm)|无|3-5mm|<1mm|
|跨时序病灶变化量化耗时|30min/例|5min/例|<60s/例|
|相似病例检索响应时间|无|3-5s|<1s|

## 表4:跨场景泛化性鲁棒性数据对比表

|量化指标|行业同类模型平均水平|本项目 LPDP-RiR 技术|
|---|---|---|
|跨医院多中心数据集 Dice 相对下降|1.5%-2.0%|<1.2%|
|低剂量 CT 影像相对 FP32 模型 Dice 损失|2.1%-3.5%|0.32%|
|床旁 CT 运动伪影场景 Dice 损失|3.2%-4.8%|0.41%|
|1mm/3mm/5mm 不同层厚 CT 影像 Dice 波动|1.0%-1.8%|<0.3%|
|国产 / 进口多品牌 CT 设备适配数量|3-5 家|12 家|
|ARM/x86 双架构硬件适配支持|部分支持|全支持|
|树莓派 4B 轻量场景适配|不支持|支持|
|连续 1000 例推理精度波动|±1.2%|±0.2%|

## 表5:算法核心模块消融实验数据表

|模型配置|Dice 相似系数|相对基线 Dice 损失|推理延迟 ( s )|显存占用 ( GB )|核心验证结论|
|---|---|---|---|---|---|
|Zig-RiR FP32 基线|0.9818|0%|0.125|15.47|全精度基准性能|
|基线 + 通用 INT8 量化|0.9702|1.18%|0.062|3.87|通用量化精度损失超临床阈值|
|基线 + 本项目分布敏感 INT8 量化|0.9809|0.09%|0.058|3.58|实现临床无损量化|
|基线 + 分布敏感 INT8 量化 + 空间域剪枝 ( 20% )|0.9725|0.95%|0.045|3.58|空间剪枝精度损失显著|
|基线 + 分布敏感 INT8 量化 + 频域剪枝 ( 20% )|0.9792|0.265%|0.040|3.58|本项目协同方案精度 - 效率最优|
|基线 + 分布敏感 INT8 量化 + 频域剪枝 + 临床后处理|0.9795|0.234%|0.041|3.58|后处理进一步优化临床可用性|

## 表6:模型训练与迭代效率对比表

|对比维度|传统 3D UNet|行业主流 Swin UNETR|本项目 LPDP-RiR 模型|
|---|---|---|---|
|模型收敛所需训练轮数|250 轮|200 轮|100 轮|
|单轮训练耗时|12min|18min|8min|
|全流程训练总耗时|50h|60h|13.3h|
|微调新场景所需数据量|≥500 例|≥300 例|≤100 例|
|单中心微调收敛周期|7 天|5 天|1 天|
|模型迭代版本更新周期|30 天|25 天|7 天|
|训练显存峰值占用|22.3GB|23.8GB|15.5GB|
|小样本学习能力 ( 100 例数据微调 Dice )|0.9125|0.9347|0.9682|

## 表7:多中心临床验证分中心性能数据表

|合作医疗机构|医院等级|入组病例数|微小结节 ( ≤5mm )占比|Dice 相似系数|HD95 ( mm )|与金标准无统计学差异 p 值|
|---|---|---|---|---|---|---|
|天津医科大学总医院|三甲|350|32%|0.9785|1.68|0.068>0.05|
|天津市环湖医院|三甲|280|27%|0.9779|1.72|0.074>0.05|
|新泰市中医医院|三级中医|220|24%|0.9772|1.75|0.081>0.05|
|基层社区卫生服务中心联合组|基层医疗机构|350|18%|0.9764|1.81|0.092>0.05|
|多中心汇总平均|-|1200|25.25%|0.9775|1.74|均 >0.05|

## 表8:细分临床场景性能专项对比表

|临床细分场景|核心指标|传统 3D UNet|行业竞品平均水平|本项目 LPDP-RiR|
|---|---|---|---|---|
|肺结节分割|Dice 相似系数|0.9124|0.9562|0.9792|
||HD95 ( mm )|7.82|2.34|1.65|
|肺肿瘤 ( ≥3cm )分割|Dice 相似系数|0.9357|0.9684|0.9825|
||HD95 ( mm )|6.25|1.98|1.58|
|肺部气管 / 血管分割|Dice 相似系数|0.8842|0.9315|0.9674|
||HD95 ( mm )|9.13|3.27|1.92|
|肺实质全结构分割|Dice 相似系数|0.9426|0.9703|0.9841|
||HD95 ( mm )|5.47|1.86|1.43|
|低剂量 CT 微小结节分割|Dice 相似系数|0.8215|0.9027|0.9683|
||病灶召回率|72.4%|88.6%|95.2%|

## 表9:全谱系硬件适配实测性能数据表

|硬件设备型号|核心算力|显存容量|推理延迟|Dice相似系数|支持功能范围|适配场景|
|---|---|---|---|---|---|---|
|NVIDIA RTX 4090|16384 CUDA核|24GB|0.022|0.9792|全功能+ 批量处理|三甲医院影像中心|
|NVIDIA Jetson AGX Orin|275 TOPS|8GB|0.040|0.9792|全功能|床旁 CT ､高端便携设备|
|NVIDIA Jetson Orin NX|100 TOPS|4GB|0.052|0.9790|全功能 (不含批量处理)|基层医院 CT 设备､便携超声|
|华为昇腾 310B|88 TOPS|8GB|0.048|0.9788|全功能|国产化医疗设备|
|树莓派 4B|4 核 Cortex-A72|无独立 GPU|无本地推理|-|报告查看､病例检索､轻量可视化|社区卫生服务中心､患者端|
|英特尔酷睿 i5 台式机(无独立 GPU )|6 核 CPU|16GB 内存|0.210|0.9785|基础分割 + 报告生成|基层卫生院､体检机构|

## 表10:医院PACS/EMR 系统兼容适配能力对比表

|适配维度|行业竞品平均水平|本项目 LPDP-RiR 平台|
|---|---|---|
|支持 DICOM3.0 核心服务|仅支持 C-STORE 基础存储|全支持 C-FIND/C-MOVE/C-STORE/C-GET 核心服务|
|支持 HL7 医疗数据标准|部分支持 HL7 v2|全支持 HL7 v2 ､ HL7 FHIR 最新标准|
|主流 PACS 系统适配数量|3-5 家|12 家(国内主流厂商全覆盖)|
|单家医院系统对接周期|15-30 天|3-7 天|
|医院现有系统改造成本|高(需改造核心接口)|零改造( SDK/DICOM 代理双模式接入)|
|数据传输加密等级|AES-128|AES-256 国密级加密|
|院内离线部署支持|部分支持|全支持(无网络环境可正常运行)|
|电子病历( EMR )无缝对接|不支持 / 需定制开发|原生支持报告自动同步至 EMR 系统|

## 表11:不同方案医院端全生命周期成本对比表

|成本维度|纯人工阅片方案|行业头部AI 方案|本项目LPDP-RiR方案|
|---|---|---|---|
|硬件投入成本(一次性)|0 元|60 万元(高端GPU服务器)|5 万元(边缘嵌入式设备)|
|软件授权年费|0 元|15 万元/年|6 万元/年(基础版)|
|人力成本(5 年累计)|480 万元(4 名全职放射科医生)|240 万元(2 名全职放射科医生)|240 万元(2 名全职放射科医生)|
|运维服务年费|0 元|2 万元/年|0 元(首5 年免费运维)|
|5 年累计总成本|480 万元|495 万元|275 万元|
|单例影像平均处理成本|26.3 元|25.8 元|15.1 元|
|医生日均阅片效率提升|基准值|75%|150%|
|5 年累计人力成本节省|基准值|240 万元|240 万元|

## 表12:肺部影像AI 主流竞品核心指标横向对比表

|对比维度|推想医疗肺结节 AI|深睿医疗肺结节 AI|联影智能 uAI 肺结节 AI|本项目 LPDP-RiR 平台|
|---|---|---|---|---|
|核心分割 Dice 相似系数|0.962|0.958|0.967|0.9792|
|单例推理延迟|0.2s|0.25s|0.18s|0.04s|
|部署模式|云端 / 院内服务器|院内服务器|院内服务器 / 设备嵌入式|边缘设备嵌入式 / 院内 / 云端全模式|
|最低硬件显存要求|16GB|16GB|12GB|4GB|
|NMPA 注册证状态|已获 II 类证|已获 II 类证|已获 II 类证|注册进行中 (预计 2027 年 Q2 拿证)|
|基层医疗机构适配性|差(硬件成本高)|差(硬件成本高)|中|优(边缘设备低成本适配)|
|手术路径规划功能|不支持|基础支持|基础支持|全支持( AR 可视化 + 动态导航)|
|设备厂商嵌入式合作模式|不支持|部分支持|仅适配自有设备|全支持(全品牌设备 SDK 嵌入)|
"""


class Introduction(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._text_targets = []
        self.create_widgets()
        self.update_language()

    def create_widgets(self):
        self._colors = {
            "bg": "#f0f7ff",
            "text": "#2c3e50",
            "muted": "#5a6b7a",
            "primary": "#2980b9",
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

        self._texts = self._build_texts()

        self._build_header(self._content)
        self._build_overview(self._content)
        self._tables_built = False
        self._tables_anchor = tk.Frame(self._content, bg=self._colors["bg"])
        self._tables_anchor.pack(fill=tk.X)
        self._build_footer(self._content)

    def update_language(self):
        for widget, key in self._text_targets:
            try:
                widget.config(text=self._t(key))
            except Exception:
                pass

        try:
            self._title_label.config(font=self._font("page_title"))
        except Exception:
            pass

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

    def on_show(self):
        if not getattr(self, "_tables_built", False):
            self._build_tables(self._tables_anchor)
            self._tables_built = True
            self.update_language()

    def _lang(self):
        return getattr(self.controller, "current_language", "CN") or "CN"

    def _t(self, key):
        if key in self._texts:
            return self._texts.get(key, {}).get(self._lang(), key)
        return languages.get_text(key, self._lang())

    def _font(self, kind):
        lang = self._lang()
        family = styles.FONT_FAMILY_CN if lang == "CN" else styles.FONT_FAMILY_EN
        if kind == "page_title":
            return (family, 24, "bold")
        if kind == "section_title":
            return (family, 18, "bold")
        if kind == "section_subtitle":
            return (family, 12)
        if kind == "body":
            return (family, 11)
        if kind == "table_header":
            return (family, 11, "bold")
        return (family, 11)

    def _register_text(self, widget, key):
        self._text_targets.append((widget, key))

    def _card(self, parent):
        return tk.Frame(
            parent,
            bg=self._colors["card"],
            highlightbackground=self._colors["border"],
            highlightthickness=1,
            bd=0,
        )

    def _section(self, parent, title_key, subtitle_key=None):
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

        if subtitle_key:
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

    def _build_header(self, parent):
        header = tk.Frame(parent, bg=self._colors["bg"])
        header.pack(fill=tk.X, padx=20, pady=(18, 8))

        self._title_label = tk.Label(
            header,
            text="",
            bg=self._colors["bg"],
            fg=self._colors["text"],
            font=self._font("page_title"),
            anchor="w",
        )
        self._title_label.pack(fill=tk.X, padx=20, pady=(0, 4))
        self._register_text(self._title_label, "page_title")

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
        subtitle.pack(fill=tk.X, padx=20)
        self._register_text(subtitle, "page_subtitle")

    def _build_overview(self, parent):
        body = self._section(parent, "overview_title", "overview_subtitle")
        card = self._card(body)
        card.pack(fill=tk.X, padx=2, pady=2)

        inner = tk.Frame(card, bg=self._colors["card"])
        inner.pack(fill=tk.X, padx=16, pady=14)

        para_keys = ["overview_p1", "overview_p2", "overview_p3", "overview_p4"]
        for k in para_keys:
            lbl = tk.Label(
                inner,
                text="",
                bg=self._colors["card"],
                fg="#34495e",
                font=self._font("body"),
                anchor="w",
                justify=tk.LEFT,
                wraplength=1050,
            )
            lbl.pack(fill=tk.X, pady=4)
            self._register_text(lbl, k)

    def _load_md_tables(self):
        lines = _EMBEDDED_BENCHMARK_MD.splitlines()
        tables = []

        i = 0
        current_title = None
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("## "):
                current_title = line[3:].strip()
                i += 1
                continue

            if current_title and line.startswith("|") and line.count("|") >= 2:
                header_cells = [c.strip() for c in line.strip("|").split("|")]
                if i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
                    sep = lines[i + 1].strip()
                    if "-" in sep:
                        i += 2
                    else:
                        i += 1
                else:
                    i += 1

                rows = []
                while i < len(lines):
                    row_line = lines[i].strip()
                    if not row_line.startswith("|"):
                        break
                    row_cells = [c.strip() for c in row_line.strip("|").split("|")]
                    if len(row_cells) < len(header_cells):
                        row_cells += [""] * (len(header_cells) - len(row_cells))
                    if len(row_cells) > len(header_cells):
                        row_cells = row_cells[: len(header_cells)]
                    rows.append(row_cells)
                    i += 1

                tables.append(
                    {"title": current_title, "headers": header_cells, "rows": rows}
                )
                current_title = None
                continue

            i += 1

        return tables

    def _build_tables(self, parent):
        section = tk.Frame(parent, bg=self._colors["bg"])
        section.pack(fill=tk.X, padx=20, pady=(10, 0))
        body = tk.Frame(section, bg=self._colors["bg"])
        body.pack(fill=tk.X, padx=20, pady=(6, 10))

        tables = self._load_md_tables()

        sections = self._table_sections()

        for t in tables:
            m = re.search(r"表\s*(\d+)", t.get("title", ""))
            if not m:
                continue
            idx = int(m.group(1))
            meta = sections.get(idx)
            if not meta:
                continue

            block = tk.Frame(body, bg=self._colors["bg"])
            block.pack(fill=tk.X, pady=10)

            title = tk.Label(
                block,
                text="",
                bg=self._colors["bg"],
                fg=self._colors["text"],
                font=self._font("section_title"),
                anchor="w",
            )
            title.pack(fill=tk.X, pady=(0, 6))

            cn_title = str(t.get("title", ""))
            cn_title = re.sub(r"^\s*表\s*\d+\s*[:：]\s*", "", cn_title)
            cn_title = re.sub(r"^\s*表\s*\d+\s*", "", cn_title).strip()

            en_title = str(meta.get("en_title", ""))
            en_title = re.sub(r"^\s*Table\s*\d+\s*:\s*", "", en_title).strip()

            self._texts[meta["title_key"]] = {
                "CN": cn_title or f"{t.get('title', '')}",
                "EN": en_title or f"{meta.get('en_title', '')}",
            }
            self._register_text(title, meta["title_key"])

            desc = tk.Label(
                block,
                text="",
                bg=self._colors["bg"],
                fg=self._colors["muted"],
                font=self._font("section_subtitle"),
                anchor="w",
                justify=tk.LEFT,
                wraplength=1100,
            )
            desc.pack(fill=tk.X, pady=(0, 8))
            self._register_text(desc, meta["desc_key"])

            card = self._card(block)
            card.pack(fill=tk.X)
            self._render_table(card, t["headers"], t["rows"])

    def _render_table(self, parent, headers, rows):
        wrap = tk.Frame(parent, bg=self._colors["card"])
        wrap.pack(fill=tk.X, padx=10, pady=10)

        columns = [f"c{i}" for i in range(len(headers))]
        tree = ttk.Treeview(
            wrap,
            columns=columns,
            show="headings",
            height=min(12, max(4, len(rows))),
        )

        vs = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        hs = ttk.Scrollbar(wrap, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        lang = self._lang()
        family = styles.FONT_FAMILY_CN if lang == "CN" else styles.FONT_FAMILY_EN
        font_body = tkfont.Font(family=family, size=10)

        for i, h in enumerate(headers):
            tree.heading(columns[i], text=h)

            sample = [h]
            for r in rows[:30]:
                if i < len(r):
                    sample.append(str(r[i]))

            width_px = min(
                520,
                max(
                    80,
                    max(font_body.measure(s) for s in sample) + 28,
                ),
            )
            tree.column(
                columns[i], width=width_px, minwidth=60, stretch=True, anchor="w"
            )

        for r in rows:
            tree.insert("", "end", values=r)

    def _table_sections(self):
        return {
            1: {
                "title_key": "t1_title",
                "desc_key": "t1_desc",
                "en_title": "Table 1: Core segmentation performance (hard metrics)",
            },
            2: {
                "title_key": "t2_title",
                "desc_key": "t2_desc",
                "en_title": "Table 2: Lightweighting effectiveness (deployment-critical metrics)",
            },
            3: {
                "title_key": "t3_title",
                "desc_key": "t3_desc",
                "en_title": "Table 3: Clinical workflow efficiency comparison",
            },
            4: {
                "title_key": "t4_title",
                "desc_key": "t4_desc",
                "en_title": "Table 4: Robustness & generalization across scenarios",
            },
            5: {
                "title_key": "t5_title",
                "desc_key": "t5_desc",
                "en_title": "Table 5: Ablation study of key modules",
            },
            6: {
                "title_key": "t6_title",
                "desc_key": "t6_desc",
                "en_title": "Table 6: Training & iteration efficiency",
            },
            7: {
                "title_key": "t7_title",
                "desc_key": "t7_desc",
                "en_title": "Table 7: Multi-center validation (site-level performance)",
            },
            8: {
                "title_key": "t8_title",
                "desc_key": "t8_desc",
                "en_title": "Table 8: Performance in fine-grained clinical scenarios",
            },
            9: {
                "title_key": "t9_title",
                "desc_key": "t9_desc",
                "en_title": "Table 9: Full-spectrum hardware compatibility & benchmarks",
            },
            10: {
                "title_key": "t10_title",
                "desc_key": "t10_desc",
                "en_title": "Table 10: PACS/EMR integration capability comparison",
            },
            11: {
                "title_key": "t11_title",
                "desc_key": "t11_desc",
                "en_title": "Table 11: Total cost of ownership (hospital lifecycle)",
            },
            12: {
                "title_key": "t12_title",
                "desc_key": "t12_desc",
                "en_title": "Table 12: Competitive benchmark (market comparison)",
            },
        }

    def _build_footer(self, parent):
        footer = tk.Frame(parent, bg=self._colors["bg"])
        footer.pack(fill=tk.X, padx=20, pady=(10, 16))

        lbl = tk.Label(
            footer,
            text="",
            bg=self._colors["bg"],
            fg="#7f8c8d",
            font=self._font("section_subtitle"),
            anchor="center",
        )
        lbl.pack(fill=tk.X, pady=8)
        self._register_text(lbl, "footer")

    def _build_texts(self):
        return {
            "page_title": {
                "CN": "项目介绍与核心性能数据",
                "EN": "Introduction & Core Performance Data",
            },
            "page_subtitle": {
                "CN": "以下内容汇总了分割精度、轻量化效果、临床效率、鲁棒性与部署兼容能力等关键证据。",
                "EN": "This page summarizes evidence across accuracy, lightweighting, clinical efficiency, robustness, and deployment compatibility.",
            },
            "overview_title": {"CN": "总体概述", "EN": "Overview"},
            "overview_subtitle": {
                "CN": "从“精度—速度—可部署性”三条主线解释 LPDP-RiR 的优势与定位。",
                "EN": "A structured overview of LPDP-RiR along accuracy, speed, and deployability.",
            },
            "overview_p1": {
                "CN": "LPDP-RiR 面向肺部 CT 结节/病灶分割与下游辅助决策，核心目标是在保持临床可用精度的前提下，实现超低延迟推理与边缘设备部署。",
                "EN": "LPDP-RiR targets lung CT lesion segmentation and downstream decision support, aiming to retain clinically usable accuracy while enabling ultra-low-latency inference and edge deployment.",
            },
            "overview_p2": {
                "CN": "模型采用分布敏感的 INT8 量化策略，并结合 20% 频域剪枝，在降低部署包体积与推理耗时的同时，将精度损失控制在临床阈值以内。",
                "EN": "The model applies distribution-aware INT8 quantization with 20% frequency-domain pruning to reduce package size and latency while keeping accuracy loss within clinical tolerance.",
            },
            "overview_p3": {
                "CN": "数据对比覆盖多个维度：与 3D UNet、nnUNet、Swin UNETR、项目基线 Zig-RiR 等模型在 Dice、HD95、IoU 等硬指标上的横向对照，以及多中心泛化和多场景鲁棒性验证。",
                "EN": "The benchmarks span hard metrics (Dice, HD95, IoU) against 3D UNet, nnUNet, Swin UNETR, the Zig-RiR baseline, plus multi-center generalization and multi-scenario robustness validation.",
            },
            "overview_p4": {
                "CN": "同时给出医院端落地所需的关键证据：PACS/EMR 兼容、DICOM/HL7 支持、硬件谱系适配、全生命周期成本对比等，便于从临床与工程两侧评估可行性。",
                "EN": "It also provides deployment evidence crucial for hospital adoption: PACS/EMR compatibility, DICOM/HL7 support, hardware coverage, and lifecycle cost comparisons for both clinical and engineering evaluation.",
            },
            "t1_desc": {
                "CN": "该表聚焦分割“硬指标”。LPDP-RiR 在 Dice、IoU、HD95 等核心指标上与金标准方案接近，同时保持对微小结节的高识别能力，适合作为临床级基础分割引擎。",
                "EN": "This table focuses on hard segmentation metrics. LPDP-RiR stays close to the gold-standard baselines on Dice/IoU/HD95 while maintaining strong detection for tiny nodules, suitable as a clinical-grade segmentation engine.",
            },
            "t2_desc": {
                "CN": "该表展示轻量化协同方案的收益：在显著降低推理延迟、部署包体积的同时，将相对 FP32 的 Dice 损失控制在较低水平，面向边缘与离线部署更友好。",
                "EN": "This table shows the benefit of the lightweighting stack: reduced latency and package size with limited Dice degradation relative to FP32, improving edge/offline deployability.",
            },
            "t3_desc": {
                "CN": "该表从临床工作流角度量化效率：单例处理、批处理、基层误诊率、路径规划耗时等，用于说明平台在真实流程中对放射科与外科协作的提升价值。",
                "EN": "This table quantifies workflow-level efficiency (single-case, batch, misdiagnosis rate, planning time), illustrating practical gains for radiology–surgery collaboration.",
            },
            "t4_desc": {
                "CN": "该表强调跨医院、多设备、多采集条件下的鲁棒性。Dice 相对下降、低剂量、运动伪影、不同层厚等指标用于判断泛化稳定性与落地风险。",
                "EN": "This table highlights robustness across hospitals, scanners, and acquisition conditions, using Dice drops under low-dose, motion artifacts, and varying slice thickness as generalization risk indicators.",
            },
            "t5_desc": {
                "CN": "该表为消融实验，说明分布敏感量化、频域剪枝与临床后处理各自对精度与延迟的贡献，为工程配置选择提供依据。",
                "EN": "This table is an ablation study showing how distribution-aware quantization, frequency pruning, and clinical post-processing contribute to accuracy and latency, guiding deployment configuration.",
            },
            "t6_desc": {
                "CN": "该表对训练与迭代效率进行对比，体现模型在训练资源、收敛速度、小样本微调能力上的优势，支持快速适配新场景与持续迭代。",
                "EN": "This table compares training/iteration efficiency, showing convergence speed, resource needs, and few-shot fine-tuning capability for rapid scenario adaptation.",
            },
            "t7_desc": {
                "CN": "该表给出多中心分中心验证数据（病例数、微小结节占比、Dice、HD95、p 值），用于支撑临床验证一致性与统计学可信度。",
                "EN": "This table provides site-level multi-center validation (cases, tiny-nodule ratio, Dice/HD95, p-values) supporting consistency and statistical credibility.",
            },
            "t8_desc": {
                "CN": "该表按细分临床场景拆解核心指标，帮助判断在不同任务（结节、肿瘤、气管/血管、全结构等）上的表现边界。",
                "EN": "This table breaks down performance by clinical sub-scenarios to understand capability boundaries across tasks.",
            },
            "t9_desc": {
                "CN": "该表覆盖全谱系硬件适配与实测性能，面向院内服务器、边缘设备、国产算力与 CPU-only 等环境，提供部署选型依据。",
                "EN": "This table covers hardware spectrum benchmarks (servers, edge devices, domestic accelerators, CPU-only) to support deployment planning.",
            },
            "t10_desc": {
                "CN": "该表为院内系统对接能力对比：DICOM/HL7、PACS 适配数量、对接周期、加密与离线部署等，体现集成成本与合规能力。",
                "EN": "This table compares hospital integration capabilities (DICOM/HL7, PACS coverage, integration cycle, encryption, offline deployment), reflecting integration cost and compliance readiness.",
            },
            "t11_desc": {
                "CN": "该表从全生命周期成本（硬件、授权、人力、运维）对比不同方案，支持医院侧 ROI 评估与采购决策。",
                "EN": "This table compares total cost of ownership (hardware, licensing, labor, maintenance) to support ROI assessment and procurement decisions.",
            },
            "t12_desc": {
                "CN": "该表为主流竞品横向对比，从精度、时延、部署模式、硬件门槛、功能范围等维度展示差异化优势。",
                "EN": "This table benchmarks against market competitors across accuracy, latency, deployment modes, hardware requirements, and feature coverage.",
            },
            "footer": {
                "CN": "© LPDP-RiR 智能医疗平台",
                "EN": "© LPDP-RiR Intelligent Medical Platform",
            },
        }


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1280x960")
    app = Introduction(root, None)
    app.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
