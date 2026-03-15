import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import os
from pathlib import Path
import numpy as np

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.append(str(APP_DIR))

from analyze3D.analyze import Analyze3DModel

try:
    import vtk
    from vtk.util import numpy_support
    import win32gui

    HAS_DEPS = True
    MISSING_DEP_MSG = ""
except ImportError as e:
    HAS_DEPS = False
    MISSING_DEP_MSG = str(e)


class VTKEmbedder(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.vtk_widget = tk.Frame(self, bg="black")
        self.vtk_widget.pack(fill=tk.BOTH, expand=True)

        self.ren_win = vtk.vtkRenderWindow()
        self.ren_win.SetOffScreenRendering(False)

        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(0.1, 0.1, 0.1)
        self.ren_win.AddRenderer(self.renderer)

        self.iren = vtk.vtkRenderWindowInteractor()
        self.iren.SetRenderWindow(self.ren_win)
        self.iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())

        self.embed_vtk_window()

        self.image_data = None
        self.plane_widget = None
        self.current_orientation = "Z"

        self.vtk_widget.bind("<Configure>", self.on_resize)

        self.iren.Initialize()

    def embed_vtk_window(self):
        try:
            tk_id = self.vtk_widget.winfo_id()
            self.ren_win.Render()
            vtk_id_str = self.ren_win.GetGenericWindowId()

            if isinstance(vtk_id_str, str) and "_p_void" in vtk_id_str:
                vtk_hwnd = int(vtk_id_str.split("_")[1], 16)
            else:
                vtk_hwnd = int(vtk_id_str)

            win32gui.SetParent(vtk_hwnd, tk_id)
            win32gui.SetWindowLong(vtk_hwnd, -16, 0x40000000 | 0x10000000)
            self.update_layout()

        except Exception as e:
            print(f"Error embedding VTK window: {e}")

    def on_resize(self, event):
        self.update_layout()
        self.ren_win.Render()

    def update_layout(self):
        try:
            width = self.vtk_widget.winfo_width()
            height = self.vtk_widget.winfo_height()
            self.ren_win.SetSize(width, height)

            vtk_id_str = self.ren_win.GetGenericWindowId()
            if isinstance(vtk_id_str, str) and "_p_void" in vtk_id_str:
                vtk_hwnd = int(vtk_id_str.split("_")[1], 16)
            else:
                vtk_hwnd = int(vtk_id_str)
            win32gui.MoveWindow(vtk_hwnd, 0, 0, width, height, True)
        except:
            pass

    def numpy_to_vtk_image(self, numpy_array):
        if not numpy_array.flags.contiguous:
            numpy_array = np.ascontiguousarray(numpy_array)

        shape = numpy_array.shape
        flat_data = numpy_array.ravel()

        vtk_data = numpy_support.numpy_to_vtk(
            num_array=flat_data, deep=True, array_type=vtk.VTK_FLOAT
        )

        img = vtk.vtkImageData()
        img.SetDimensions(shape[2], shape[1], shape[0])
        img.GetPointData().SetScalars(vtk_data)

        return img

    def update_data(self, np_data):
        if np_data is None:
            return

        if self.plane_widget:
            self.plane_widget.Off()
            self.plane_widget.SetInteractor(None)
            self.plane_widget = None

        self.renderer.RemoveAllViewProps()

        self.image_data = self.numpy_to_vtk_image(np_data)

        outline = vtk.vtkOutlineFilter()
        outline.SetInputData(self.image_data)
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(outline.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        self.renderer.AddActor(actor)

        self.plane_widget = vtk.vtkImagePlaneWidget()
        self.plane_widget.SetInputData(self.image_data)
        self.plane_widget.SetInteractor(self.iren)

        self.plane_widget.SetLeftButtonAction(
            vtk.vtkImagePlaneWidget.VTK_SLICE_MOTION_ACTION
        )
        self.plane_widget.SetMiddleButtonAction(
            vtk.vtkImagePlaneWidget.VTK_WINDOW_LEVEL_ACTION
        )
        self.plane_widget.SetRightButtonAction(
            vtk.vtkImagePlaneWidget.VTK_CURSOR_ACTION
        )

        self.plane_widget.DisplayTextOn()
        self.plane_widget.On()

        self.set_orientation(self.current_orientation)

        self.renderer.ResetCamera()
        self.ren_win.Render()

    def set_orientation(self, axis):
        self.current_orientation = axis
        if not self.plane_widget or not self.image_data:
            return

        dims = self.image_data.GetDimensions()

        if axis == "X":
            self.plane_widget.SetPlaneOrientationToXAxes()
            self.plane_widget.SetSliceIndex(dims[0] // 2)
        elif axis == "Y":
            self.plane_widget.SetPlaneOrientationToYAxes()
            self.plane_widget.SetSliceIndex(dims[1] // 2)
        elif axis == "Z":
            self.plane_widget.SetPlaneOrientationToZAxes()
            self.plane_widget.SetSliceIndex(dims[2] // 2)

        self.ren_win.Render()


class AnalyzeApp(tk.Tk):
    def __init__(self, initial_file=None):
        super().__init__()
        self.title("3D分析查看器")
        self.geometry("1000x800")

        try:
            icon_path = APP_DIR / "logo" / "logo.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception:
            pass

        if not HAS_DEPS:
            messagebox.showerror("错误", f"缺少依赖:\n{MISSING_DEP_MSG}")
            self.destroy()
            return

        self.model = Analyze3DModel()

        self.create_ui()

        if initial_file and os.path.exists(initial_file):
            self.load_file_path(initial_file)

    def create_ui(self):
        control_frame = ttk.Frame(self, padding=5)
        control_frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(control_frame, text="加载 NPZ 文件", command=self.load_file).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Label(control_frame, text="当前模式:").pack(side=tk.LEFT, padx=5)
        self.combo_keys = ttk.Combobox(control_frame, state="readonly")
        self.combo_keys.pack(side=tk.LEFT, padx=5)
        self.combo_keys.bind("<<ComboboxSelected>>", self.on_key_selected)

        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(
            side=tk.LEFT, padx=10, fill=tk.Y
        )
        ttk.Label(control_frame, text="视图:").pack(side=tk.LEFT, padx=2)

        self.orientation_var = tk.StringVar(value="Z")
        for text, val in [
            ("轴状位 (Z)", "Z"),
            ("冠状位 (Y)", "Y"),
            ("矢状位 (X)", "X"),
        ]:
            ttk.Radiobutton(
                control_frame,
                text=text,
                variable=self.orientation_var,
                value=val,
                command=lambda: self.embedder.set_orientation(
                    self.orientation_var.get()
                ),
            ).pack(side=tk.LEFT, padx=2)

        ttk.Label(
            control_frame,
            text="左键拖动：移动切片 / 旋转（边缘）。中键：调整窗宽窗位。",
        ).pack(side=tk.RIGHT, padx=5)

        self.embedder = VTKEmbedder(self)
        self.embedder.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

    def load_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("NPZ 文件", "*.npz"), ("所有文件", "*.*")]
        )
        if file_path:
            self.load_file_path(file_path)

    def load_file_path(self, file_path):
        keys = self.model.load_file(file_path)
        self.combo_keys["values"] = keys
        if keys:
            self.combo_keys.current(0)
            self.update_visualization()

    def on_key_selected(self, event):
        key = self.combo_keys.get()
        if self.model.set_current_data(key):
            self.update_visualization()

    def update_visualization(self):
        data = self.model.get_data()
        if data is not None:
            self.embedder.update_data(data)


if __name__ == "__main__":
    initial_file = None
    if len(sys.argv) > 1:
        initial_file = sys.argv[1]
    app = AnalyzeApp(initial_file=initial_file)
    app.mainloop()
