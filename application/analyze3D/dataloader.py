import numpy as np


def _normalize_input(a):
    if a.ndim == 3:
        return a
    if a.ndim == 4:
        c0 = a.shape[0]
        c_last = a.shape[-1]
        if c0 <= 4 and c0 != c_last:
            return a[0]
        return a[..., 0]
    raise ValueError("NPZ 内未找到有效的三维数组")


def _resample_to_shape_nn(a, target=(256, 256, 256)):
    if a.ndim != 3:
        raise ValueError("体数据维度必须为 3")
    tz, ty, tx = target
    sz, sy, sx = a.shape
    idx_z = np.clip((np.arange(tz) * (sz / tz)).astype(np.int64), 0, sz - 1)
    tmp = np.take(a, idx_z, axis=0)
    idx_y = np.clip((np.arange(ty) * (sy / ty)).astype(np.int64), 0, sy - 1)
    tmp = np.take(tmp, idx_y, axis=1)
    idx_x = np.clip((np.arange(tx) * (sx / tx)).astype(np.int64), 0, sx - 1)
    tmp = np.take(tmp, idx_x, axis=2)
    return tmp.astype(np.float32)


class NPZDataLoader:
    def __init__(self):
        self.raw_data = {}
        self.valid_3d_keys = []

    def load_npz(self, path):
        self.raw_data = {}
        self.valid_3d_keys = []
        try:
            with np.load(path) as npz:
                for key in npz.files:
                    try:
                        arr = npz[key]
                        vol = _normalize_input(arr)
                        self.raw_data[key] = vol
                        self.valid_3d_keys.append(key)
                    except Exception:
                        continue

            if "data" in self.valid_3d_keys:
                self.valid_3d_keys.remove("data")
                self.valid_3d_keys.insert(0, "data")

            return len(self.valid_3d_keys) > 0
        except Exception as e:
            print(f"Error loading NPZ file {path}: {e}")
            return False

    def get_3d_array(self, key):
        if key in self.raw_data:
            vol = self.raw_data[key]
            return _resample_to_shape_nn(vol, (256, 256, 256))
        return None
