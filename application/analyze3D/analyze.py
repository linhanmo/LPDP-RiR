import numpy as np

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
