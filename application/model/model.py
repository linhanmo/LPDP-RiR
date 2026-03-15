import argparse
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.append(str(APP_DIR))

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

try:
    import torch
except ImportError:
    pass

from pathlib import Path
from datetime import datetime
import numpy as np
from scipy import ndimage

try:
    from application.medical_analysis.lesion_classifier import LesionClassifier
    from application.medical_analysis.surgical_planner import SurgicalPlanner
    from application.medical_analysis.report_generator import ReportGenerator
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from medical_analysis.lesion_classifier import LesionClassifier
    from medical_analysis.surgical_planner import SurgicalPlanner
    from medical_analysis.report_generator import ReportGenerator

try:
    from PIL import Image, ImageDraw
except Exception:
    Image = None
    ImageDraw = None

try:
    import onnxruntime as ort
except Exception:
    ort = None

try:
    import torch
except Exception:
    torch = None

import os
import sys
import importlib.util

KERNELS_DIR = Path(__file__).resolve().parent.parent.parent / "kernels"

MIN_LESION_DIAMETER_MM = 1.5


def _enable_pytorch_fallback():
    p = KERNELS_DIR / "wkv_fallback.py"
    if p.exists():
        spec = importlib.util.spec_from_file_location("wkv_fallback", str(p))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if "wkv_cuda" not in sys.modules:
                sys.modules["wkv_cuda"] = mod
            if "wkv" not in sys.modules:
                sys.modules["wkv"] = mod
            os.environ.setdefault("RWKV_FORCE_FALLBACK", "1")


_enable_pytorch_fallback()


import sqlite3
import hashlib
import secrets
import hmac

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.append(str(APP_DIR))

try:
    from data.database import get_connection, init_db
    from data.dataloader import get_current_user
except ImportError:
    pass


def record_run(
    ts: str,
    input_dir: Path,
    output_dir: Path,
    username: str | None = None,
    created_at: str | None = None,
):
    init_db()
    u = username
    if not u:
        u = get_current_user()

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO datastorage(username, foldername) VALUES(?,?)",
            (u, ts),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        if u is not None:
            try:
                conn.execute(
                    "INSERT INTO datastorage(username, foldername) VALUES(?,?)",
                    (None, ts),
                )
                conn.commit()
            except Exception:
                pass
    except Exception as e:
        print(f"Error recording run: {e}")
    finally:
        conn.close()


def select_file(title, filetypes):
    return None


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def load_3d_data(path: Path):
    if not path.exists():
        raise FileNotFoundError(str(path))
    if path.suffix.lower() == ".npy":
        arr = np.load(str(path))
    elif path.suffix.lower() == ".npz":
        npz = np.load(str(path), allow_pickle=True)
        keys = list(npz.keys())
        if not keys:
            raise ValueError("npz文件为空")
        preferred = ["data", "image", "images"]
        arr = None
        for k in preferred:
            if k in npz:
                arr = npz[k]
                break
        if arr is None:
            arr = npz[keys[0]]
        if isinstance(arr, np.ndarray) and arr.dtype == object and arr.shape == ():
            arr = arr.item()
    else:
        raise ValueError("仅支持.npy或.npz文件作为3D数据输入")
    if arr.ndim not in (3, 4):
        raise ValueError("输入数据需为3D或4D数组")
    return arr


def slices_from_volume(vol: np.ndarray):
    if vol.ndim == 3:
        for i in range(vol.shape[0]):
            yield i, vol[i]
    else:
        if vol.shape[0] <= 4 and vol.shape[1] > 1:
            for i in range(vol.shape[1]):
                yield i, vol[:, i]
        else:
            for i in range(vol.shape[0]):
                yield i, vol[i]


def normalize_to_uint8(arr: np.ndarray):
    a = np.asarray(arr, dtype=np.float32)
    m, M = float(a.min()), float(a.max())
    if M > m:
        a = (a - m) / (M - m)
    else:
        a = np.zeros_like(a)
    a = (a * 255.0).clip(0, 255).astype(np.uint8)
    return a


def window_to_uint8(arr: np.ndarray, center: float, width: float):
    a = np.asarray(arr, dtype=np.float32)
    lo = center - width / 2.0
    hi = center + width / 2.0
    a = np.clip(a, lo, hi)
    a = (a - lo) / max(hi - lo, 1e-6)
    return (a * 255.0).clip(0, 255).astype(np.uint8)


def stretch_to_uint8(arr: np.ndarray, p_low: float, p_high: float, bounds=None):
    a = np.asarray(arr, dtype=np.float32)
    if bounds is None:
        lo = float(np.percentile(a, p_low))
        hi = float(np.percentile(a, p_high))
    else:
        lo, hi = float(bounds[0]), float(bounds[1])
    if hi <= lo:
        return normalize_to_uint8(a)
    a = np.clip(a, lo, hi)
    a = (a - lo) / (hi - lo)
    return (a * 255.0).clip(0, 255).astype(np.uint8)


def equalize_hist_u8(u8: np.ndarray):
    hist = np.bincount(u8.ravel(), minlength=256)
    cdf = hist.cumsum()
    cdf = (cdf - cdf.min()) / max(cdf.max() - cdf.min(), 1)
    lut = np.floor(255 * cdf).astype(np.uint8)
    return lut[u8]


def to_cdhw(vol: np.ndarray):
    a = np.asarray(vol)
    if a.ndim == 3:
        return a[None, ...]
    if a.ndim == 4:
        if a.shape[0] <= 8:
            return a
        if a.shape[-1] <= 8:
            d_axis = int(np.argmin(a.shape[:3]))
            if d_axis == 0:
                return np.transpose(a, (3, 0, 1, 2))
            if d_axis == 1:
                return np.transpose(a, (3, 1, 0, 2))
            return np.transpose(a, (3, 2, 0, 1))
        return np.transpose(a, (0, 3, 1, 2))
    raise ValueError("不支持的体数据维度")


def center_crop_or_pad_3d(cdhw: np.ndarray, tgt_d: int, tgt_h: int, tgt_w: int):
    C, D, H, W = cdhw.shape
    out = np.zeros((C, tgt_d, tgt_h, tgt_w), dtype=cdhw.dtype)
    d0 = max((tgt_d - D) // 2, 0)
    h0 = max((tgt_h - H) // 2, 0)
    w0 = max((tgt_w - W) // 2, 0)
    sd0 = max((D - tgt_d) // 2, 0)
    sh0 = max((H - tgt_h) // 2, 0)
    sw0 = max((W - tgt_w) // 2, 0)
    d1 = sd0 + min(D, tgt_d)
    h1 = sh0 + min(H, tgt_h)
    w1 = sw0 + min(W, tgt_w)
    out[:, d0 : d0 + (d1 - sd0), h0 : h0 + (h1 - sh0), w0 : w0 + (w1 - sw0)] = cdhw[
        :, sd0:d1, sh0:h1, sw0:w1
    ]
    return out


def resize_volume_3d(
    cdhw: np.ndarray, tgt_d: int, tgt_h: int, tgt_w: int, mode: str = "trilinear"
):
    if torch is None:
        return center_crop_or_pad_3d(cdhw, tgt_d, tgt_h, tgt_w)
    t = torch.from_numpy(cdhw[None, ...]).float()
    with torch.no_grad():
        t2 = torch.nn.functional.interpolate(
            t, size=(tgt_d, tgt_h, tgt_w), mode=mode, align_corners=False
        )
    return t2[0].detach().cpu().numpy()


def resize_mask_3d(mask: np.ndarray, out_shape: tuple):
    if torch is None:
        return mask
    t = torch.from_numpy(mask[None, None, ...].astype(np.float32))
    with torch.no_grad():
        t2 = torch.nn.functional.interpolate(t, size=out_shape, mode="nearest")
    return t2[0, 0].detach().cpu().numpy().astype(mask.dtype)


def resize_probs_3d(probs: np.ndarray, out_shape: tuple):
    if torch is None:
        return probs
    t = torch.from_numpy(probs[None, ...].astype(np.float32))
    with torch.no_grad():
        t2 = torch.nn.functional.interpolate(
            t, size=out_shape, mode="trilinear", align_corners=False
        )
    return t2[0].detach().cpu().numpy()


def colorize_mask(mask2d: np.ndarray, num_classes: int):
    palette = [
        (0, 0, 0),
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (255, 255, 0),
        (255, 0, 255),
        (0, 255, 255),
        (255, 165, 0),
        (128, 0, 128),
    ]
    rgb = np.zeros((mask2d.shape[0], mask2d.shape[1], 3), dtype=np.uint8)
    for c in range(num_classes):
        col = palette[c % len(palette)]
        sel = mask2d == c
        if np.any(sel):
            rgb[sel] = np.array(col, dtype=np.uint8)
    return rgb


def heatmap_rgb(prob2d: np.ndarray):
    p = np.clip(prob2d.astype(np.float32), 0.0, 1.0)
    r = np.clip(4 * p - 1.5, 0, 1)
    g = np.clip(4 * p - 0.5, 0, 1)
    b = np.clip(4 * p + 0.5, 0, 1)
    img = np.stack([r, g, b], axis=-1)
    return (img * 255).astype(np.uint8)


def postprocess_binary(mask2d: np.ndarray, keep_components: int = 2, min_size: int = 0):
    try:
        import scipy.ndimage as ndi
    except Exception:
        return mask2d
    m = mask2d.astype(bool)
    se = np.ones((3, 3), dtype=bool)
    m = ndi.binary_closing(m, structure=se)
    m = ndi.binary_fill_holes(m)
    labeled, n = ndi.label(m)
    if n == 0:
        return m.astype(np.uint8)
    sizes = np.bincount(labeled.ravel())
    sizes[0] = 0
    order = np.argsort(sizes)[::-1]
    keep = order[: max(keep_components, 1)]
    keep_set = set(int(x) for x in keep)
    if min_size > 0:
        small_ids = [i for i, s in enumerate(sizes) if s < min_size]
        for sid in small_ids:
            if sid in keep_set:
                keep_set.remove(sid)
    out = np.isin(labeled, list(keep_set))
    return out.astype(np.uint8)


def detect_and_draw_lesions(
    img_rgb: np.ndarray,
    mask_2d: np.ndarray,
    probs_map: np.ndarray,
    draw_color: tuple,
    slice_idx: int = 0,
    min_size: int = 10,
):
    if Image is None or ImageDraw is None:
        return img_rgb, []

    try:
        import scipy.ndimage as ndi
    except Exception:
        return img_rgb, []

    labeled, num_features = ndi.label(mask_2d > 0)

    lesion_info = []

    pil_img = Image.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_img)

    if num_features > 0:
        objects = ndi.find_objects(labeled)
        for i, sl in enumerate(objects):
            if sl is None:
                continue

            obj_mask = labeled == (i + 1)
            size = obj_mask.sum()

            if size < min_size:
                continue

            conf = 0.0
            if probs_map is not None:
                if probs_map.ndim == 3 and probs_map.shape[0] > 1:
                    conf = float(probs_map[1][obj_mask].mean())
                elif probs_map.ndim == 2:
                    conf = float(probs_map[obj_mask].mean())

            cy, cx = ndi.center_of_mass(obj_mask)

            dy, dx = sl
            y0, y1 = dy.start, dy.stop
            x0, x1 = dx.start, dx.stop

            try:
                import cv2

                cnt_img = obj_mask.astype(np.uint8)
                contours, _ = cv2.findContours(
                    cnt_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
                )
                for cnt in contours:
                    pts = [tuple(pt[0]) for pt in cnt]
                    if len(pts) > 1:
                        draw.line(pts + [pts[0]], fill=draw_color, width=2)
            except ImportError:
                eroded = ndi.binary_erosion(obj_mask)
                boundary = obj_mask ^ eroded
                by, bx = np.where(boundary)
                points = list(zip(bx, by))
                draw.point(points, fill=draw_color)

            cl = 3
            draw.line([(cx - cl, cy), (cx + cl, cy)], fill=draw_color, width=1)
            draw.line([(cx, cy - cl), (cx, cy + cl)], fill=draw_color, width=1)

            text_str = str(i + 1)
            draw.text((cx + 2, cy + 2), text_str, fill=draw_color)

            lesion_info.append(
                {
                    "slice": slice_idx,
                    "id": i + 1,
                    "pos": (int(cx), int(cy)),
                    "conf": conf,
                    "bbox": (int(x0), int(y0), int(x1), int(y1)),
                }
            )

    return np.array(pil_img), lesion_info


def generate_report(
    ts: str,
    vol: np.ndarray,
    recon_mask,
    recon_probs,
    input_dir: Path,
    output_dir: Path,
    model_info,
    contrast: str,
    robust_low: float,
    robust_high: float,
    window_center,
    window_width: float,
    fg_classes: str,
    overlay_alpha: float,
    prob_threshold: float,
    input_path: Path,
    weights_path: Path,
    lang: str = "zh",
    lesion_data: list = None,
):
    texts = {
        "zh": {
            "title": "分析报告",
            "basic_info": "基本信息",
            "timestamp": "时间戳",
            "input_file": "输入文件",
            "weights_file": "权重文件",
            "model_type": "模型类型",
            "contrast_mode": "对比度模式",
            "robust_percentile": "鲁棒百分位",
            "window": "窗口",
            "fg_classes": "前景类别",
            "overlay_alpha": "叠加透明度",
            "prob_threshold": "概率阈值",
            "data_stats": "数据统计",
            "dimensions": "维度",
            "value_range": "值范围",
            "mean_std": "均值/标准差",
            "percentiles": "百分位",
            "seg_stats": "分割统计",
            "num_classes": "类别数",
            "fg_ratio": "前景占比",
            "conn_components": "连通组件数量",
            "category": "类别",
            "voxel_count": "体素数",
            "img_preview": "图像预览",
            "none": "无",
            "suspected_lesions": "疑似病灶详情",
            "lesion_id": "ID",
            "slice_idx": "切片索引",
            "position": "位置(X,Y)",
            "confidence": "置信度",
            "switch_lang": "Switch to English",
            "show_more": "显示更多",
        },
        "en": {
            "title": "Analysis Report",
            "basic_info": "Basic Information",
            "timestamp": "Timestamp",
            "input_file": "Input File",
            "weights_file": "Weights File",
            "model_type": "Model Type",
            "contrast_mode": "Contrast Mode",
            "robust_percentile": "Robust Percentile",
            "window": "Window",
            "fg_classes": "Foreground Classes",
            "overlay_alpha": "Overlay Alpha",
            "prob_threshold": "Probability Threshold",
            "data_stats": "Data Statistics",
            "dimensions": "Dimensions",
            "value_range": "Value Range",
            "mean_std": "Mean/Std Dev",
            "percentiles": "Percentiles",
            "seg_stats": "Segmentation Statistics",
            "num_classes": "Number of Classes",
            "fg_ratio": "Foreground Ratio",
            "conn_components": "Connected Components",
            "category": "Category",
            "voxel_count": "Voxel Count",
            "img_preview": "Image Preview",
            "none": "None",
            "suspected_lesions": "Suspected Lesion Details",
            "lesion_id": "ID",
            "slice_idx": "Slice Index",
            "position": "Position(X,Y)",
            "confidence": "Confidence",
            "switch_lang": "切换到中文",
            "show_more": "Show More",
        },
    }

    def _t(key):
        zh = texts["zh"].get(key, key)
        en = texts["en"].get(key, key)
        return f'<span class="lang-zh">{zh}</span><span class="lang-en" style="display:none">{en}</span>'

    init_zh_display = "inline" if lang == "zh" else "none"
    init_en_display = "inline" if lang == "en" else "none"

    a = np.asarray(vol, dtype=np.float32)
    cdhw = to_cdhw(a)
    C, D, H, W = cdhw.shape
    vmin = float(a.min())
    vmax = float(a.max())
    vmean = float(a.mean())
    vstd = float(a.std())
    p1 = float(np.percentile(a, 1.0))
    p50 = float(np.percentile(a, 50.0))
    p99 = float(np.percentile(a, 99.0))
    cls_counts = {}
    n_components = None
    fg_ratio = None
    num_classes = None
    if recon_mask is not None:
        u, c = np.unique(recon_mask.astype(np.int32), return_counts=True)
        for ui, ci in zip(u.tolist(), c.tolist()):
            cls_counts[int(ui)] = int(ci)
        total = int(D * H * W)
        fg = total - cls_counts.get(0, 0)
        fg_ratio = (fg / total) if total > 0 else None
        try:
            import scipy.ndimage as ndi

            lab, n = ndi.label((recon_mask > 0).astype(np.uint8))
            n_components = int(n)
        except Exception:
            n_components = None
    if recon_probs is not None:
        num_classes = int(recon_probs.shape[0])
    imgs = []
    idxs = [0, max(D // 2, 0), max(D - 1, 0)]
    for i in idxs:
        names = [
            output_dir / f"proc_{i:03d}_overlay.png",
            output_dir / f"proc_{i:03d}_color.png",
            output_dir / f"proc_{i:03d}_mask.png",
            input_dir / f"slice_{i:03d}.png",
        ]
        for n in names:
            if n.exists():
                imgs.append(str(n))
                break
    lesion_analyses = []
    surgical_plans = []

    if recon_mask is not None:
        try:
            classifier = LesionClassifier(pixel_spacing=(1.0, 1.0, 1.0))
            planner = SurgicalPlanner(pixel_spacing=(1.0, 1.0, 1.0))

            labeled_mask, num_candidates = ndimage.label(recon_mask)
            all_slices = ndimage.find_objects(labeled_mask)

            for i in range(1, num_candidates + 1):
                slices = all_slices[i - 1]
                if slices is None:
                    continue

                mask_i = labeled_mask == i
                crop_vol = vol[slices]
                crop_mask = mask_i[slices]

                analysis = classifier.analyze(crop_mask, crop_vol)
                if not analysis:
                    continue

                if analysis["diameter_mm"] < MIN_LESION_DIAMETER_MM:
                    continue

                center = ndimage.center_of_mass(mask_i)
                center_int = (int(center[0]), int(center[1]), int(center[2]))
                analysis["pos"] = center_int
                analysis["id"] = len(lesion_analyses) + 1

                lesion_analyses.append(analysis)

                if (
                    "High" in analysis["risk_level"]
                    or "Moderate" in analysis["risk_level"]
                ):
                    path, entry, risk, metrics = planner.plan_puncture_path(
                        vol, center_int
                    )

                    description = planner.generate_path_description(
                        entry,
                        center_int,
                        metrics,
                        lesion_diameter=analysis["diameter_mm"],
                    )

                    surgical_plans.append(
                        {
                            "id": analysis["id"],
                            "path": path,
                            "entry": entry,
                            "risk": risk,
                            "metrics": metrics,
                            "description": description,
                        }
                    )

        except Exception as e:
            print(f"Error during advanced analysis: {e}", file=sys.stderr)

    reporter = ReportGenerator(output_dir)

    try:
        new_report_path = reporter.generate(
            patient_id=input_path.name,
            lesion_analyses=lesion_analyses,
            surgical_plans=surgical_plans,
            output_filename="report.html",
            images=imgs if imgs else [],
        )

        filename = "report.html"
        report_path = output_dir / filename

        import json

        info = {
            "ts": ts,
            "input_path": str(input_path),
            "lesion_analyses": lesion_analyses,
            "surgical_plans_count": len(surgical_plans),
        }
        (output_dir / "report.json").write_text(
            json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return

    except Exception as e:
        print(f"Failed to generate advanced report: {e}", file=sys.stderr)
        pass

    html = []
    html.append(
        f"""<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{_t('title')}</title><style>
        body{{font-family:Arial,Helvetica,sans-serif;padding:20px}}
        h2{{border-bottom:1px solid #ddd;padding-bottom:4px}}
        table{{border-collapse:collapse;width:100%}}
        td,th{{border:1px solid #ccc;padding:6px;text-align:left}}
        code{{background:#f6f8fa;padding:2px 4px;border-radius:4px}}
        .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));grid-gap:12px}}
        .lang-zh{{display:{init_zh_display}}}
        .lang-en{{display:{init_en_display}}}
        .hidden-row{{display:none}}
        table.expanded .hidden-row{{display:table-row}}
        .btn{{padding:8px 16px;background:#007bff;color:white;border:none;border-radius:4px;cursor:pointer;margin-bottom:10px}}
        .btn:hover{{background:#0056b3}}
        </style>
        <script>
        function toggleLang() {{
            var zhs = document.getElementsByClassName('lang-zh');
            var ens = document.getElementsByClassName('lang-en');
            var isZh = zhs[0].style.display !== 'none';
            var newZh = isZh ? 'none' : 'inline';
            var newEn = isZh ? 'inline' : 'none';
            for(var i=0; i<zhs.length; i++) zhs[i].style.display = newZh;
            for(var i=0; i<ens.length; i++) ens[i].style.display = newEn;
        }}
        function toggleTable(btn) {{
            var table = document.getElementById('lesionTable');
            table.classList.toggle('expanded');
            if (table.classList.contains('expanded')) {{
                btn.style.display = 'none'; 
            }}
        }}
        </script>
        </head><body>"""
    )
    html.append(
        f'<button class="btn" onclick="toggleLang()">{_t("switch_lang")}</button>'
    )
    html.append(f"<h1>{_t('title')}</h1>")
    html.append(f"<h2>{_t('basic_info')}</h2>")
    html.append("<table>")
    html.append(f"<tr><th>{_t('timestamp')}</th><td>{ts}</td></tr>")
    html.append(f"<tr><th>{_t('input_file')}</th><td>{str(input_path)}</td></tr>")
    html.append(
        f"<tr><th>{_t('weights_file')}</th><td>{str(weights_path) if weights_path is not None else _t('none')}</td></tr>"
    )
    html.append(
        f"<tr><th>{_t('model_type')}</th><td>{model_info.get('type','none')}</td></tr>"
    )
    html.append(f"<tr><th>{_t('contrast_mode')}</th><td>{contrast}</td></tr>")
    html.append(
        f"<tr><th>{_t('robust_percentile')}</th><td>{robust_low} / {robust_high}</td></tr>"
    )
    html.append(
        f"<tr><th>{_t('window')}</th><td>{'center=' + str(window_center) + ', width=' + str(window_width) if (window_center is not None and window_width is not None) else _t('none')}</td></tr>"
    )
    html.append(f"<tr><th>{_t('fg_classes')}</th><td>{fg_classes}</td></tr>")
    html.append(f"<tr><th>{_t('overlay_alpha')}</th><td>{overlay_alpha}</td></tr>")
    html.append(f"<tr><th>{_t('prob_threshold')}</th><td>{prob_threshold}</td></tr>")
    html.append("</table>")
    html.append(f"<h2>{_t('data_stats')}</h2>")
    html.append("<table>")
    html.append(
        f"<tr><th>{_t('dimensions')}</th><td>C={C}, D={D}, H={H}, W={W}</td></tr>"
    )
    html.append(
        f"<tr><th>{_t('value_range')}</th><td>min={vmin:.3f}, max={vmax:.3f}</td></tr>"
    )
    html.append(
        f"<tr><th>{_t('mean_std')}</th><td>mean={vmean:.3f}, std={vstd:.3f}</td></tr>"
    )
    html.append(
        f"<tr><th>{_t('percentiles')}</th><td>p1={p1:.3f}, p50={p50:.3f}, p99={p99:.3f}</td></tr>"
    )
    html.append("</table>")
    if recon_mask is not None:
        html.append(f"<h2>{_t('seg_stats')}</h2>")
        html.append("<table>")
        if num_classes is not None:
            html.append(f"<tr><th>{_t('num_classes')}</th><td>{num_classes}</td></tr>")
        if fg_ratio is not None:
            html.append(f"<tr><th>{_t('fg_ratio')}</th><td>{fg_ratio:.4f}</td></tr>")
        if n_components is not None:
            html.append(
                f"<tr><th>{_t('conn_components')}</th><td>{n_components}</td></tr>"
            )
        html.append("</table>")
        if cls_counts:
            html.append("<table>")
            html.append(
                f"<tr><th>{_t('category')}</th><th>{_t('voxel_count')}</th></tr>"
            )
            for k in sorted(cls_counts.keys()):
                html.append(f"<tr><td>{k}</td><td>{cls_counts[k]}</td></tr>")
            html.append("</table>")

    if lesion_data:
        html.append(f"<h2>{_t('suspected_lesions')}</h2>")
        html.append("<table id='lesionTable'>")
        html.append(
            f"<tr><th>{_t('slice_idx')}</th><th>{_t('lesion_id')}</th><th>{_t('position')}</th><th>{_t('confidence')}</th></tr>"
        )

        for i, l in enumerate(lesion_data):
            row_class = "hidden-row" if i >= 50 else ""
            html.append(
                f"<tr class='{row_class}'><td>{l['slice']}</td><td>{l['id']}</td><td>{l['pos']}</td><td>{l['conf']:.4f}</td></tr>"
            )

        html.append("</table>")
        if len(lesion_data) > 50:
            html.append(
                f'<div style="margin-top:10px"><button class="btn" onclick="toggleTable(this)">{_t("show_more")}</button></div>'
            )

    if imgs:
        html.append(f"<h2>{_t('img_preview')}</h2>")
        html.append('<div class="grid">')
        import base64

        for im in imgs:
            try:
                b = Path(im).read_bytes()
                b64 = base64.b64encode(b).decode("ascii")
                src = "data:image/png;base64," + b64
                html.append(
                    f'<div><img src="{src}" style="width:100%;height:auto;border:1px solid #ccc"></div>'
                )
            except Exception:
                rel = os.path.relpath(im, output_dir)
                html.append(
                    f'<div><img src="{rel}" style="width:100%;height:auto;border:1px solid #ccc"></div>'
                )
        html.append("</div>")
    html.append("</body></html>")

    filename = "report.html"

    report_path = output_dir / filename
    report_path.write_text("\n".join(html), encoding="utf-8")
    info = {
        "ts": ts,
        "input_path": str(input_path),
        "weights_path": str(weights_path) if weights_path is not None else None,
        "model_type": model_info.get("type", "none"),
        "shape": {"C": C, "D": D, "H": H, "W": W},
        "stats": {
            "min": vmin,
            "max": vmax,
            "mean": vmean,
            "std": vstd,
            "p1": p1,
            "p50": p50,
            "p99": p99,
        },
        "classes": cls_counts,
        "components": n_components,
        "foreground_ratio": fg_ratio,
    }
    import json

    (output_dir / "report.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def save_image(arr2d: np.ndarray, path: Path, prefer_png: bool = True):
    if Image is None:
        raise RuntimeError("保存PNG需要安装Pillow库")
    img = Image.fromarray(arr2d)
    img.save(str(path))


def save_image_rgb(arr3: np.ndarray, path: Path):
    if Image is None:
        raise RuntimeError("保存PNG需要安装Pillow库")
    img = Image.fromarray(arr3, mode="RGB")
    img.save(str(path))


def load_model(weights_path: Path):
    if weights_path is None:
        return {"type": "none", "impl": None}
    if not weights_path.exists():
        return {"type": "none", "impl": None}
    suf = weights_path.suffix.lower()
    if suf == ".onnx" and ort is not None:
        sess = ort.InferenceSession(
            str(weights_path), providers=["CPUExecutionProvider"]
        )
        return {"type": "onnx", "impl": sess}
    if suf in (".pt", ".pth") and torch is not None:
        try:
            state = torch.load(str(weights_path), map_location="cpu")
        except Exception:
            state = None
        if state is not None:
            sd = state.get("model", state) if isinstance(state, dict) else state
            try:
                from Zig_RiR3d import Z_RiR

                model = Z_RiR(in_channels=1, out_channels=2)
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                model.to(device)
                if isinstance(sd, dict):
                    model.load_state_dict(sd, strict=False)
                model.eval()
                return {"type": "pytorch", "impl": model, "device": device}
            except Exception:
                pass
        try:
            model = torch.jit.load(str(weights_path), map_location="cpu")
            model.eval()
            return {"type": "torchscript", "impl": model}
        except Exception:
            return {"type": "none", "impl": None}
    return {"type": "none", "impl": None}


def run_inference(model_info, slice2d: np.ndarray):
    h, w = slice2d.shape
    x = slice2d.astype(np.float32)
    m, M = float(x.min()), float(x.max())
    if M > m:
        x = (x - m) / (M - m)
    x = x.reshape(1, 1, h, w).astype(np.float32)
    if model_info["type"] == "onnx":
        sess = model_info["impl"]
        inp_name = sess.get_inputs()[0].name
        y = sess.run(None, {inp_name: x})[0]
        y = np.asarray(y)
        y = y.squeeze()
        return normalize_to_uint8(y)
    if model_info.get("type") == "torchscript":
        model = model_info["impl"]
        with torch.no_grad():
            t = torch.from_numpy(x)
            y = model(t).detach().cpu().numpy()
        y = np.asarray(y).squeeze()
        return normalize_to_uint8(y)
    return normalize_to_uint8(slice2d)


def infer_full_volume(model_info, vol: np.ndarray):
    if model_info.get("type") != "pytorch":
        return None
    cdhw_orig = to_cdhw(vol)
    if cdhw_orig.shape[0] > 1:
        cdhw_orig = cdhw_orig[0:1]
    C, D0, H0, W0 = cdhw_orig.shape
    cdhw_t = resize_volume_3d(cdhw_orig, 49, 192, 192, mode="trilinear")
    x = cdhw_t.astype(np.float32)
    m, M = float(x.min()), float(x.max())
    if M > m:
        x = (x - m) / (M - m)
    t = torch.from_numpy(x[None, ...])
    device = model_info.get("device", torch.device("cpu"))
    model = model_info["impl"]
    with torch.no_grad():
        t = t.to(device)
        try:
            logits = model(t)
        except TypeError:
            logits = model(t)
        probs = torch.softmax(logits, dim=1).detach().cpu().numpy()[0]
        mask = np.argmax(probs, axis=0)
    probs_res = resize_probs_3d(probs, (D0, H0, W0))
    mask_res = resize_mask_3d(mask, (D0, H0, W0))
    return {"mask": mask_res, "probs": probs_res}


def infer_full_volume_cpu(
    vol: np.ndarray,
    contrast: str,
    robust_low: float,
    robust_high: float,
    window_center: float,
    window_width: float,
    global_bounds,
    keep_components: int,
    min_size: int,
):
    cdhw = to_cdhw(vol)
    C, D, H, W = cdhw.shape
    mask = np.zeros((D, H, W), dtype=np.uint8)
    probs = np.zeros((2, D, H, W), dtype=np.float32)
    for idx, s in slices_from_volume(vol):
        if window_center is not None and window_width is not None:
            s_u8 = window_to_uint8(s, window_center, window_width)
        elif contrast == "slice":
            s_u8 = stretch_to_uint8(s, robust_low, robust_high)
        elif contrast == "volume" and global_bounds is not None:
            s_u8 = stretch_to_uint8(s, robust_low, robust_high, bounds=global_bounds)
        elif contrast == "equalize":
            s_u8 = stretch_to_uint8(s, 1.0, 99.0)
            s_u8 = equalize_hist_u8(s_u8)
        else:
            s_u8 = normalize_to_uint8(s)
        p_bg = s_u8.astype(np.float32) / 255.0
        p_lung = 1.0 - p_bg
        probs[0, idx] = p_bg
        probs[1, idx] = p_lung
        m2d = np.argmax(probs[:, idx], axis=0).astype(np.uint8)
        m2d = postprocess_binary(
            (m2d == 1).astype(np.uint8),
            keep_components=keep_components,
            min_size=min_size,
        )
        mask[idx] = (m2d > 0).astype(np.uint8)
    return {"mask": mask, "probs": probs}


def run_analysis_and_save(
    vol: np.ndarray,
    model_info: dict,
    input_save_dir: Path,
    output_save_dir: Path,
    contrast: str = "slice",
    robust_low: float = 1.0,
    robust_high: float = 99.0,
    window_center: float = None,
    window_width: float = None,
    fg_classes: str = "1",
    overlay_alpha: float = 0.6,
    prob_threshold: float = 0.5,
    binary_components: int = 2,
    binary_min_size: int = 500,
    prefer_png: bool = True,
    progress_callback=None,
):
    if vol.ndim == 4 and vol.shape[0] == 1:
        vol = vol[0]

    total_slices = int(vol.shape[0]) if hasattr(vol, "shape") and vol.ndim >= 3 else 0
    if callable(progress_callback):
        try:
            progress_callback(0, total_slices, "slices")
        except Exception:
            pass

    global_bounds = None
    if contrast == "volume":
        a = np.asarray(vol, dtype=np.float32)
        global_bounds = (
            float(np.percentile(a, robust_low)),
            float(np.percentile(a, robust_high)),
        )

    pred_vol = None
    if model_info.get("type") == "pytorch":
        pred_vol = infer_full_volume(model_info, vol)
        if pred_vol is None:
            print("PyTorch模型推理失败，退回CPU模式", file=sys.stderr)

    if pred_vol is None:
        pred_vol = infer_full_volume_cpu(
            vol,
            contrast,
            robust_low,
            robust_high,
            window_center,
            window_width,
            global_bounds,
            binary_components,
            binary_min_size,
        )

    recon_inputs = []
    recon_binary = []
    recon_color = []
    recon_overlay = []
    recon_mask = None
    recon_probs = None

    if pred_vol is not None:
        recon_mask = pred_vol["mask"].astype(np.uint8)
        recon_probs = pred_vol["probs"].astype(np.float32)

    fg_set = {int(x) for x in str(fg_classes).split(",") if x.strip() != ""}

    result_paths = {
        "inputs": [],
        "mask": [],
        "binary": [],
        "color": [],
        "overlay": [],
        "binary_anno": [],
        "mask_anno": [],
        "color_anno": [],
        "overlay_anno": [],
    }

    all_lesion_data = []

    processed = 0
    for idx, s in slices_from_volume(vol):
        if window_center is not None and window_width is not None:
            s_u8 = window_to_uint8(s, window_center, window_width)
        elif contrast == "slice":
            s_u8 = stretch_to_uint8(s, robust_low, robust_high)
        elif contrast == "volume" and global_bounds is not None:
            s_u8 = stretch_to_uint8(s, robust_low, robust_high, bounds=global_bounds)
        elif contrast == "equalize":
            s_u8 = stretch_to_uint8(s, 1.0, 99.0)
            s_u8 = equalize_hist_u8(s_u8)
        else:
            s_u8 = normalize_to_uint8(s)

        in_name = input_save_dir / f"slice_{idx:03d}.png"
        save_image(s_u8, in_name, prefer_png=prefer_png)
        recon_inputs.append(s_u8)
        result_paths["inputs"].append(str(in_name))

        if pred_vol is not None:
            mask = np.asarray(pred_vol["mask"][idx]).astype(np.uint8)
            probs = np.asarray(pred_vol["probs"][:, idx]).astype(np.float32)
            num_classes = int(probs.shape[0])

            y_u8 = (mask.astype(np.float32) / max(num_classes - 1, 1) * 255.0).astype(
                np.uint8
            )
            out_name = output_save_dir / f"proc_{idx:03d}_mask.png"
            save_image(y_u8, out_name, prefer_png=prefer_png)
            result_paths["mask"].append(str(out_name))

            for c in range(num_classes):
                hm = heatmap_rgb(np.clip(probs[c], 0, 1))
                out_name = output_save_dir / f"prob_c{c}_{idx:03d}.png"
                save_image_rgb(hm, out_name)
                k = f"prob_c{c}"
                if k not in result_paths:
                    result_paths[k] = []
                result_paths[k].append(str(out_name))

            fg_mask = np.isin(mask, list(fg_set)).astype(np.uint8)
            b = postprocess_binary(
                fg_mask,
                keep_components=int(binary_components),
                min_size=int(binary_min_size),
            )
            y_bin = (b > 0).astype(np.uint8) * 255
            out_name = output_save_dir / f"proc_{idx:03d}_binary.png"
            save_image(y_bin, out_name, prefer_png=prefer_png)
            recon_binary.append(y_bin)
            result_paths["binary"].append(str(out_name))

            mask_rgb = np.stack([y_u8, y_u8, y_u8], axis=-1)
            _, lesion_info = detect_and_draw_lesions(
                mask_rgb, fg_mask, probs, (255, 0, 0), idx, binary_min_size
            )
            all_lesion_data.extend(lesion_info)

            rgb = colorize_mask(mask, num_classes)
            out_name = output_save_dir / f"proc_{idx:03d}_color.png"
            save_image_rgb(rgb, out_name)
            recon_color.append(rgb)
            result_paths["color"].append(str(out_name))

            if Image is not None and prefer_png:
                base = np.stack([s_u8, s_u8, s_u8], axis=-1).astype(np.float32)
                overlay = base.copy()
                alpha = float(max(0.0, min(1.0, overlay_alpha)))

                for c in range(num_classes):
                    col = np.array(
                        colorize_mask(np.full_like(mask, c), num_classes)[0, 0],
                        dtype=np.float32,
                    )
                    sel_c = mask == c
                    if np.any(sel_c):
                        overlay[sel_c] = (1 - alpha) * base[sel_c] + alpha * col

                thr = float(max(0.0, min(1.0, prob_threshold)))
                for c in range(num_classes):
                    sel_prob = probs[c] > thr
                    if np.any(sel_prob):
                        col = np.array(
                            colorize_mask(np.full_like(mask, c), num_classes)[0, 0],
                            dtype=np.float32,
                        )
                        overlay[sel_prob] = (1 - alpha) * base[sel_prob] + alpha * col

                overlay = overlay.clip(0, 255).astype(np.uint8)
                out_name = output_save_dir / f"proc_{idx:03d}_overlay.png"
                save_image_rgb(overlay, out_name)
                recon_overlay.append(overlay)
                result_paths["overlay"].append(str(out_name))

        processed += 1
        if callable(progress_callback):
            try:
                progress_callback(processed, total_slices, "slices")
            except Exception:
                pass

    if recon_inputs:
        try:
            recon = {"input_u8": np.stack(recon_inputs, axis=0)}
            if len(recon_binary) == len(recon_inputs) and len(recon_binary) > 0:
                recon["binary_u8"] = np.stack(recon_binary, axis=0)
            if len(recon_color) > 0:
                recon["color_rgb"] = np.stack(recon_color, axis=0)
            if len(recon_overlay) > 0:
                recon["overlay_rgb"] = np.stack(recon_overlay, axis=0)
            if recon_mask is not None:
                recon["mask"] = recon_mask
            if recon_probs is not None:
                recon["probs"] = recon_probs
            np.savez(str(output_save_dir / "recon.npz"), **recon)

            import json

            with open(output_save_dir / "lesion_data.json", "w", encoding="utf-8") as f:
                json.dump(all_lesion_data, f, indent=2)

        except Exception:
            pass

    return result_paths, recon_mask, recon_probs, all_lesion_data


def main():
    _enable_pytorch_fallback()
    ds = None
    APP_DIR = Path(__file__).resolve().parent.parent

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--weights", type=str, default=str(APP_DIR / "best_model.pth"))
    args = parser.parse_args()
    contrast = "slice"
    robust_low = 1.0
    robust_high = 99.0
    window_center = None
    window_width = None
    fg_classes = "1"
    overlay_alpha = 0.6
    prob_threshold = 0.5
    binary_components = 2
    binary_min_size = 5

    base_input_dir = APP_DIR / "input"
    base_output_dir = APP_DIR / "output"
    ensure_dir(base_input_dir)
    ensure_dir(base_output_dir)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    created_at = datetime.now().isoformat(timespec="seconds")

    input_save_dir = base_input_dir / ts
    output_save_dir = base_output_dir / ts
    ensure_dir(input_save_dir)
    ensure_dir(output_save_dir)

    print(f"OUTPUT_DIR: {output_save_dir.resolve()}")
    print(f"INPUT_DIR: {input_save_dir.resolve()}")

    username = None
    try:
        username = get_current_user()
    except Exception:
        pass

    try:
        record_run(
            ts,
            input_save_dir,
            output_save_dir,
            username=username,
            created_at=created_at,
        )
    except Exception:
        pass

    weights_path = Path(args.weights) if args.weights else None
    input_path = Path(args.input)

    vol = load_3d_data(input_path)
    model_info = (
        load_model(weights_path)
        if weights_path is not None
        else {"type": "none", "impl": None}
    )

    _vol_for_total = (
        vol[0] if getattr(vol, "ndim", 0) == 4 and vol.shape[0] == 1 else vol
    )
    total_slices = (
        int(_vol_for_total.shape[0])
        if hasattr(_vol_for_total, "shape") and _vol_for_total.ndim >= 3
        else 0
    )
    print(f"PROGRESS: 0/{total_slices}", flush=True)

    def _progress_printer(current: int, total: int, stage: str):
        if total is None or int(total) <= 0:
            return
        print(f"PROGRESS: {int(current)}/{int(total)}", flush=True)

    if torch is not None:
        dev = model_info.get("device", torch.device("cpu"))
        print(
            f"CUDA可用: {'是' if torch.cuda.is_available() else '否'}，使用设备: {dev}"
        )

    result_paths, recon_mask, recon_probs, lesion_data = run_analysis_and_save(
        vol,
        model_info,
        input_save_dir,
        output_save_dir,
        contrast,
        float(robust_low),
        float(robust_high),
        window_center,
        window_width,
        fg_classes,
        float(overlay_alpha),
        float(prob_threshold),
        int(binary_components),
        int(binary_min_size),
        prefer_png=True,
        progress_callback=_progress_printer,
    )

    try:
        print("PROGRESS_STAGE: report", flush=True)
        generate_report(
            ts,
            vol,
            recon_mask,
            recon_probs,
            input_save_dir,
            output_save_dir,
            model_info,
            contrast,
            float(robust_low),
            float(robust_high),
            window_center,
            window_width if window_width is not None else None,
            fg_classes,
            float(overlay_alpha),
            float(prob_threshold),
            input_path,
            weights_path,
            lang="zh",
            lesion_data=lesion_data,
        )
        print("PROGRESS_STAGE: done", flush=True)
    except Exception:
        import traceback

        traceback.print_exc()
        pass

    print(f"输入切片已保存到: {input_save_dir}")
    print(f"处理结果已保存到: {output_save_dir}")
    print(f"OUTPUT_DIR: {output_save_dir}")


if __name__ == "__main__":
    main()
