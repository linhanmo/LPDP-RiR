import numpy as np
from scipy import ndimage
from application.medical_analysis.guideline_engine import GuidelineEngine


class LesionClassifier:
    def __init__(self, pixel_spacing=(1.0, 1.0, 1.0)):
        self.spacing = np.array(pixel_spacing)
        self.guideline_engine = GuidelineEngine()

    def analyze(self, lesion_mask, lesion_img):
        if lesion_mask.sum() == 0:
            return None

        voxel_count = lesion_mask.sum()
        volume_mm3 = voxel_count * np.prod(self.spacing)

        diameter_mm = 2 * (3 * volume_mm3 / (4 * np.pi)) ** (1 / 3)

        valid_voxels = lesion_img[lesion_mask > 0]
        mean_intensity = valid_voxels.mean()
        std_intensity = valid_voxels.std()
        min_intensity = valid_voxels.min()
        max_intensity = valid_voxels.max()

        lesion_type = "Unknown"
        risk_level = "Unknown"

        engine_density = "Solid"
        if mean_intensity > 200:
            density_type = "Calcified (钙化)"
            engine_density = "Calcified"
        elif mean_intensity < -300:
            density_type = "Ground Glass (磨玻璃)"
            engine_density = "Ground Glass"
        else:
            density_type = "Solid (实性)"
            engine_density = "Solid"

        guideline_result = self.guideline_engine.calculate_lung_rads(
            diameter_mm, engine_density
        )

        if engine_density == "Calcified":
            risk_level = "Low (低风险)"
            recommendation = "Routine annual follow-up recommended. (建议年度常规随访)"
            lung_rads = "1"
        else:
            lung_rads = guideline_result.get("lung_rads_score", "N/A")
            risk_str = guideline_result.get("risk_percent", "")

            if lung_rads in ["1", "2"]:
                risk_level = f"Low (低风险) - Lung-RADS {lung_rads}"
            elif lung_rads in ["3"]:
                risk_level = f"Intermediate (中风险) - Lung-RADS {lung_rads}"
            elif lung_rads in ["4A", "4B", "4X"]:
                risk_level = f"High (高风险) - Lung-RADS {lung_rads}"
            else:
                risk_level = f"Unknown - Lung-RADS {lung_rads}"

            rec_zh = guideline_result.get("recommendation_zh", "")
            rec_en = guideline_result.get("recommendation_en", "")
            recommendation = f"{rec_en} ({rec_zh})"

        if diameter_mm < 3:
            size_category = "Micronodule (微小结节)"
        elif diameter_mm < 10:
            size_category = "Nodule (小结节)"
        elif diameter_mm < 30:
            size_category = "Large Nodule (大结节)"
        else:
            size_category = "Mass (肿块)"
            if engine_density != "Calcified":
                risk_level = "Very High (极高风险)"
                recommendation = "Urgent surgical intervention and multidisciplinary team (MDT) review required. (需紧急手术干预及多学科团队(MDT)评估)"

        treatment_plan = None
        surgical_path = None
        stage_info = None

        if diameter_mm >= 6 or lung_rads in ["4A", "4B", "4X"]:
            t_stage, stage_group = self.guideline_engine.estimate_stage(diameter_mm)

            treatment_plan = self.guideline_engine.get_treatment_plan(
                stage_group, patient_age=65, comorbidities=[]
            )

            surgical_path = self.guideline_engine.recommend_surgical_path(
                diameter_mm, location="peripheral", lesion_type=engine_density
            )

            stage_info = {"t_stage": t_stage, "clinical_stage_group": stage_group}

        return {
            "volume_mm3": float(volume_mm3),
            "diameter_mm": float(diameter_mm),
            "mean_hu": float(mean_intensity),
            "std_hu": float(std_intensity),
            "min_hu": float(min_intensity),
            "max_hu": float(max_intensity),
            "density_type": density_type,
            "size_category": size_category,
            "risk_level": risk_level,
            "recommendation": recommendation,
            "lung_rads_score": lung_rads,
            "guideline_data": guideline_result,
            "stage_info": stage_info,
            "treatment_plan": treatment_plan,
            "surgical_path": surgical_path,
        }
