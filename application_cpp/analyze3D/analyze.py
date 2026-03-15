import numpy as np
import sys
from pathlib import Path

try:
    from PIL import Image
except Exception:
    Image = None

try:
    from .dataloader import NPZDataLoader
except ImportError:
    from dataloader import NPZDataLoader


class Analyze3DModel:
    def __init__(self):
        self.loader = NPZDataLoader()
        self.current_data = None
        self.current_key = None
        self.valid_keys = []

    def load_file(self, file_path):
        if self.loader.load_npz(file_path):
            self.valid_keys = self.loader.valid_3d_keys
            if self.valid_keys:
                self.set_current_data(self.valid_keys[0])
            return self.valid_keys
        return []

    def set_current_data(self, key):
        if key in self.valid_keys:
            self.current_key = key
            self.current_data = self.loader.get_3d_array(key)
            return True
        return False

    def get_data(self):
        return self.current_data

    def get_data_range(self):
        if self.current_data is not None:
            return float(self.current_data.min()), float(self.current_data.max())
        return 0.0, 1.0


def _normalize_to_uint8(a: np.ndarray):
    x = np.asarray(a, dtype=np.float32)
    m = float(np.nanmin(x))
    M = float(np.nanmax(x))
    if M > m:
        x = (x - m) / (M - m)
    else:
        x = np.zeros_like(x)
    x = np.clip(x * 255.0, 0.0, 255.0).astype(np.uint8)
    return x


def export_slices(vol: np.ndarray, out_dir: Path, axes: str = "Z"):
    if Image is None:
        raise RuntimeError("PIL 未安装，无法导出 PNG 切片。")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    vol = np.asarray(vol)
    if vol.ndim != 3:
        raise ValueError("体数据维度必须为 3")

    axes = "".join([c for c in axes.upper() if c in ("X", "Y", "Z")]) or "Z"
    axis_map = {
        "X": (2, lambda i: vol[:, :, i]),
        "Y": (1, lambda i: vol[:, i, :]),
        "Z": (0, lambda i: vol[i, :, :]),
    }

    total = 0
    for ax in axes:
        total += int(vol.shape[axis_map[ax][0]])

    done = 0
    print(f"PROGRESS: 0/{total}", flush=True)
    for ax in axes:
        axis_dir = out_dir / f"axis_{ax}"
        axis_dir.mkdir(parents=True, exist_ok=True)
        n = int(vol.shape[axis_map[ax][0]])
        getter = axis_map[ax][1]
        for i in range(n):
            u8 = _normalize_to_uint8(getter(i))
            Image.fromarray(u8, mode="L").save(axis_dir / f"slice_{i:03d}.png")
            done += 1
            if done % 2 == 0 or done == total:
                print(f"PROGRESS: {done}/{total}", flush=True)


def main(argv=None):
    import argparse
    import json
    from datetime import datetime

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--outdir", type=str, default=None)
    parser.add_argument("--key", type=str, default=None)
    parser.add_argument("--axes", type=str, default="Z")
    args = parser.parse_args(argv)

    m = Analyze3DModel()
    keys = m.load_file(args.input)
    if not keys:
        raise RuntimeError("NPZ 内未找到有效的三维数组")

    key = args.key if args.key in keys else keys[0]
    ok = m.set_current_data(key)
    if not ok:
        raise RuntimeError("无法切换到所选数据键")

    base = Path(__file__).resolve().parent.parent
    if args.outdir:
        out_dir = Path(args.outdir)
    else:
        out_dir = base / "output" / ("analyze3d_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"OUTPUT_DIR: {out_dir.resolve()}", flush=True)
    meta = {
        "input": str(Path(args.input).resolve()),
        "keys": list(keys),
        "key": key,
        "shape": list(m.get_data().shape) if m.get_data() is not None else None,
        "range": list(m.get_data_range()),
        "axes": "".join([c for c in args.axes.upper() if c in ("X", "Y", "Z")]) or "Z",
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print("PROGRESS_STAGE: slices", flush=True)
    export_slices(m.get_data(), out_dir, axes=meta["axes"])
    print("PROGRESS_STAGE: done", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
