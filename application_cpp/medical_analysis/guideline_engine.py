import json
import os


class GuidelineEngine:
    def __init__(self, data_path=None):
        if data_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.join(current_dir, "..", "data", "nccn_guidelines.json")
            treatment_path = os.path.join(
                current_dir, "..", "data", "treatment_guidelines.json"
            )

        self.data = {}
        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            print(f"Warning: Guidelines data not found at {data_path}")

        self.treatment_data = {}
        if os.path.exists(treatment_path):
            with open(treatment_path, "r", encoding="utf-8") as f:
                self.treatment_data = json.load(f)
        else:
            print(f"Warning: Treatment data not found at {treatment_path}")

    def estimate_stage(self, diameter_mm):
        rules = self.treatment_data.get("staging_rules", {}).get("T_stage", [])
        t_stage = "Tx"
        for rule in rules:
            if diameter_mm <= rule["max_size"]:
                t_stage = rule["stage"]
                break

        stage_group = (
            self.treatment_data.get("staging_rules", {})
            .get("stage_grouping", {})
            .get(t_stage, "Unknown")
        )
        return t_stage, stage_group

    def get_treatment_plan(self, stage_group, patient_age=60, comorbidities=None):
        if comorbidities is None:
            comorbidities = []

        protocols = self.treatment_data.get("treatment_protocols", {}).get(
            stage_group, {}
        )
        if not protocols:
            return None

        primary_options = []
        modifiers = self.treatment_data.get("weight_modifiers", {})

        raw_options = protocols.get("primary", [])

        for opt in raw_options:
            base_weight = opt.get("weight", 50)
            final_weight = base_weight
            opt_type = opt.get("type", "unknown")

            if patient_age > 75:
                mod = modifiers.get("age_gt_75", {})
                final_weight += mod.get(opt_type, 0)
                if "surgery" in opt_type and opt_type not in mod:
                    final_weight += mod.get("surgery", 0)

            if "COPD" in comorbidities:
                mod = modifiers.get("comorbidity_copd", {})
                final_weight += mod.get(opt_type, 0)
                if "surgery" in opt_type and opt_type not in mod:
                    final_weight += mod.get("surgery", 0)

            if "Poor Performance" in comorbidities:
                mod = modifiers.get("performance_status_poor", {})
                final_weight += mod.get(opt_type, 0)

            option_entry = {
                "name_zh": opt["name_zh"],
                "name_en": opt["name_en"],
                "type": opt_type,
                "weight": final_weight,
                "desc_zh": opt.get("description_zh", ""),
                "desc_en": opt.get("description_en", ""),
            }

            if "procedures" in opt:
                option_entry["procedures"] = opt["procedures"]
            if "components" in opt:
                option_entry["components"] = opt["components"]

            primary_options.append(option_entry)

        primary_options.sort(key=lambda x: x["weight"], reverse=True)
        return primary_options

    def recommend_surgical_path(
        self, diameter_mm, location="peripheral", lesion_type="Solid"
    ):
        path_data = self.treatment_data.get("surgical_path_planning", {})

        recommendations = {"approach": [], "resection": []}

        for approach in path_data.get("approaches", []):
            valid = True
            if (
                "indication_size_max" in approach
                and diameter_mm > approach["indication_size_max"]
            ):
                valid = False

            if valid:
                recommendations["approach"].append(approach)

        for resection in path_data.get("resection_types", []):
            rule = resection.get("rule", "")
            is_match = False
            try:
                ctx = {
                    "size": diameter_mm,
                    "location": location,
                    "type": lesion_type,
                    "margin_check": "pass",
                }
                rid = resection["id"]
                if rid == "wedge":
                    if (
                        diameter_mm < 20
                        and location == "peripheral"
                        and lesion_type == "Ground Glass"
                    ):
                        is_match = True
                elif rid == "segment":
                    if diameter_mm < 20:
                        is_match = True
                elif rid == "lobe":
                    if diameter_mm >= 20 or location == "central":
                        is_match = True

                if is_match:
                    recommendations["resection"].append(resection)
            except:
                pass

        return recommendations

    def calculate_lung_rads(self, diameter_mm, density_type, growth_status="stable"):
        score = "1"
        reason_en = "No significant nodules."
        reason_zh = "无显著结节。"

        if density_type == "Solid":
            if diameter_mm < 6:
                score = "2"
                reason_en = f"Solid nodule < 6mm ({diameter_mm:.1f}mm)."
                reason_zh = f"实性结节 < 6mm ({diameter_mm:.1f}mm)。"
            elif 6 <= diameter_mm < 8:
                if growth_status == "stable":
                    score = "3"
                    reason_en = f"Solid nodule 6-8mm ({diameter_mm:.1f}mm), stable."
                    reason_zh = f"实性结节 6-8mm ({diameter_mm:.1f}mm)，稳定。"
                else:
                    score = "4A"
                    reason_en = (
                        f"Solid nodule 6-8mm ({diameter_mm:.1f}mm), new or growing."
                    )
                    reason_zh = f"实性结节 6-8mm ({diameter_mm:.1f}mm)，新发或生长。"
            elif 8 <= diameter_mm < 15:
                if growth_status == "stable":
                    score = "4A"
                    reason_en = f"Solid nodule 8-15mm ({diameter_mm:.1f}mm), stable."
                    reason_zh = f"实性结节 8-15mm ({diameter_mm:.1f}mm)，稳定。"
                else:
                    score = "4B"
                    reason_en = f"Solid nodule 8-15mm ({diameter_mm:.1f}mm), growing."
                    reason_zh = f"实性结节 8-15mm ({diameter_mm:.1f}mm)，生长。"
            elif diameter_mm >= 15:
                score = "4B"
                reason_en = f"Solid nodule >= 15mm ({diameter_mm:.1f}mm)."
                reason_zh = f"实性结节 >= 15mm ({diameter_mm:.1f}mm)。"

        elif density_type == "Part-Solid":
            if diameter_mm < 6:
                score = "2"
                reason_en = f"Part-solid nodule < 6mm ({diameter_mm:.1f}mm)."
                reason_zh = f"部分实性结节 < 6mm ({diameter_mm:.1f}mm)。"
            elif diameter_mm >= 6:
                score = "4A"
                reason_en = f"Part-solid nodule >= 6mm ({diameter_mm:.1f}mm)."
                reason_zh = f"部分实性结节 >= 6mm ({diameter_mm:.1f}mm)。"
                if diameter_mm >= 8:
                    score = "4B"

        elif density_type == "Ground Glass":
            if diameter_mm < 30:
                if diameter_mm < 20:
                    score = "2"
                    reason_en = f"Ground glass nodule < 20mm ({diameter_mm:.1f}mm)."
                    reason_zh = f"磨玻璃结节 < 20mm ({diameter_mm:.1f}mm)。"
                else:
                    score = "3"
                    reason_en = f"Ground glass nodule >= 20mm ({diameter_mm:.1f}mm)."
                    reason_zh = f"磨玻璃结节 >= 20mm ({diameter_mm:.1f}mm)。"
            else:
                score = "3"

        elif density_type == "Calcified":
            score = "1"
            reason_en = "Calcified benign nodule."
            reason_zh = "钙化良性结节。"

        risk_info = self.data.get("risk_levels", {}).get(score, {})

        rec_key = "annual"
        if score == "3":
            rec_key = "6mo"
        elif score == "4A":
            rec_key = "3mo"
        elif score == "4B" or score == "4X":
            rec_key = "biopsy"

        rec_info = self.data.get("follow_up_text", {}).get(rec_key, {})

        return {
            "lung_rads_score": score,
            "risk_percent": risk_info.get("risk_zh", ""),
            "risk_desc_en": risk_info.get("desc_en", ""),
            "risk_desc_zh": risk_info.get("desc_zh", ""),
            "recommendation_en": rec_info.get("en", ""),
            "recommendation_zh": rec_info.get("zh", ""),
            "basis_en": reason_en,
            "basis_zh": reason_zh,
        }

    def recommend_surgery(self, diameter_mm):
        rules = self.data.get("surgical_rules", [])
        for rule in rules:
            if diameter_mm < rule["max_size"]:
                return {
                    "procedure_en": rule["type_en"],
                    "procedure_zh": rule["type_zh"],
                    "reason_en": rule["reason_en"],
                    "reason_zh": rule["reason_zh"],
                }
        if rules:
            rule = rules[-1]
            return {
                "procedure_en": rule["type_en"],
                "procedure_zh": rule["type_zh"],
                "reason_en": rule["reason_en"],
                "reason_zh": rule["reason_zh"],
            }
        return None
