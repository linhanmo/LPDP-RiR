import numpy as np
import heapq
from scipy import ndimage
from .guideline_engine import GuidelineEngine


class SurgicalPlanner:
    def __init__(self, pixel_spacing=(1.0, 1.0, 1.0)):
        self.spacing = np.array(pixel_spacing)
        self.guideline_engine = GuidelineEngine()

    def plan_puncture_path(self, vol, target_pos_zxy):
        tz, ty, tx = target_pos_zxy
        tz, ty, tx = int(tz), int(ty), int(tx)

        D, H, W = vol.shape

        best_entry = None
        min_dist = float("inf")

        candidates = []
        step_size = 4
        for y in range(0, H, step_size):
            candidates.append((tz, y, 0))
            candidates.append((tz, y, W - 1))
        for x in range(0, W, step_size):
            candidates.append((tz, 0, x))
            candidates.append((tz, H - 1, x))

        real_candidates = []
        for z, y, x in candidates:
            vec = np.array([tz - z, ty - y, tx - x])
            dist = np.linalg.norm(vec * self.spacing)
            if dist == 0:
                continue
            step = vec / np.linalg.norm(vec)

            curr = np.array([z, y, x], dtype=float)
            found_skin = False

            max_steps = int(np.linalg.norm(vec)) * 2
            for _ in range(max_steps):
                cz, cy, cx = int(curr[0]), int(curr[1]), int(curr[2])
                if 0 <= cz < D and 0 <= cy < H and 0 <= cx < W:
                    if vol[cz, cy, cx] > -600:
                        real_candidates.append((cz, cy, cx))
                        found_skin = True
                        break
                curr += step
                if not (0 <= curr[0] < D and 0 <= curr[1] < H and 0 <= curr[2] < W):
                    break

            if not found_skin:
                real_candidates.append((z, y, x))

        best_path = []
        best_risk = float("inf")
        best_metrics = {}

        for start_node in real_candidates:
            risk = 0
            path = self._get_line(start_node, (tz, ty, tx))

            for z, y, x in path:
                if 0 <= z < D and 0 <= y < H and 0 <= x < W:
                    val = vol[z, y, x]
                    if val > 300:
                        risk += 1000
                    elif val > 100:
                        risk += 5
                    elif val > -600:
                        risk += 1
                    else:
                        risk += 0.1

            p1 = np.array(start_node) * self.spacing
            p2 = np.array([tz, ty, tx]) * self.spacing
            length_mm = np.linalg.norm(p1 - p2)

            total_score = risk + length_mm * 0.5

            if total_score < best_risk:
                best_risk = total_score
                best_entry = start_node
                best_path = path

                dz = (tz - start_node[0]) * self.spacing[0]
                dy = (ty - start_node[1]) * self.spacing[1]
                dx = (tx - start_node[2]) * self.spacing[2]

                angle_axial = np.degrees(np.arctan2(dy, dx))
                dist_xy = np.sqrt(dx**2 + dy**2)
                angle_vertical = np.degrees(np.arctan2(dz, dist_xy))

                best_metrics = {
                    "depth_mm": length_mm,
                    "angle_axial": angle_axial,
                    "angle_vertical": angle_vertical,
                }

        return best_path, best_entry, best_risk, best_metrics

    def generate_path_description(self, entry, target, metrics, lesion_diameter=None):

        depth = metrics.get("depth_mm", 0)
        ax_angle = metrics.get("angle_axial", 0)
        vt_angle = metrics.get("angle_vertical", 0)

        dz = entry[0] - target[0]
        dy = entry[1] - target[1]
        dx = entry[2] - target[2]

        direction_en = []
        direction_zh = []

        if abs(dx) > 5:
            if dx > 0:
                direction_en.append("Left")
                direction_zh.append("左侧")
            else:
                direction_en.append("Right")
                direction_zh.append("右侧")

        if abs(dy) > 5:
            if dy > 0:
                direction_en.append("Posterior")
                direction_zh.append("后方")
            else:
                direction_en.append("Anterior")
                direction_zh.append("前方")

        if abs(dz) > 5:
            if dz > 0:
                direction_en.append("Inferior")
                direction_zh.append("下方")
            else:
                direction_en.append("Superior")
                direction_zh.append("上方")

        dir_str_en = " / ".join(direction_en) if direction_en else "Direct"
        dir_str_zh = " / ".join(direction_zh) if direction_zh else "直接"

        desc_en = (
            f"Entry point located {dir_str_en} relative to the lesion. "
            f"Trajectory length is {depth:.1f} mm. "
            f"Approach requires {abs(ax_angle):.1f}° {'Left' if ax_angle < 0 else 'Right'} axial rotation and "
            f"{abs(vt_angle):.1f}° {'Caudal' if vt_angle < 0 else 'Cranial'} tilt."
        )

        desc_zh = (
            f"进针点位于病灶{dir_str_zh}。 "
            f"轨迹长度为 {depth:.1f} mm。 "
            f"进针路径需要轴向旋转 {abs(ax_angle):.1f}° ({'左' if ax_angle < 0 else '右'}) 以及 "
            f"{abs(vt_angle):.1f}° {'尾向' if vt_angle < 0 else '头向'} 倾斜。"
        )

        if lesion_diameter is not None:
            surgery_rec = self.guideline_engine.recommend_surgery(lesion_diameter)
            if surgery_rec:
                proc_en = surgery_rec.get("procedure_en", "")
                reason_en = surgery_rec.get("reason_en", "")
                desc_en += f" Based on lesion size ({lesion_diameter:.1f}mm), recommended procedure: {proc_en}. Reason: {reason_en}"

                proc_zh = surgery_rec.get("procedure_zh", "")
                reason_zh = surgery_rec.get("reason_zh", "")
                desc_zh += f" 基于病灶大小 ({lesion_diameter:.1f}mm)，推荐手术方式：{proc_zh}。理由：{reason_zh}"

        return {"en": desc_en, "zh": desc_zh}

    def _get_line(self, start, end):
        p1 = np.array(start)
        p2 = np.array(end)
        dist = np.linalg.norm(p2 - p1)
        if dist == 0:
            return [tuple(p1)]

        num_points = int(dist)
        path = []
        for i in range(num_points + 1):
            t = i / max(1, num_points)
            p = p1 + t * (p2 - p1)
            path.append((int(p[0]), int(p[1]), int(p[2])))
        return path
