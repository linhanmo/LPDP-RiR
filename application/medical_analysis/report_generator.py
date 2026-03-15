import os
import sys
from datetime import datetime
import json
import base64
from pathlib import Path

try:
    from application.data.config_manager import get_language
except ImportError:

    def get_language():
        return "CN"


class ReportGenerator:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(
        self,
        patient_id,
        lesion_analyses,
        surgical_plans,
        output_filename="medical_report.html",
        images=None,
    ):

        num_lesions = len(lesion_analyses)
        max_risk = "Low"
        for l in lesion_analyses:
            if "High" in l["risk_level"]:
                max_risk = "High"
            elif "Moderate" in l["risk_level"] and max_risk != "High":
                max_risk = "Moderate"

        status_color = "#28a745"
        if "High" in max_risk:
            status_color = "#dc3545"
        elif "Moderate" in max_risk:
            status_color = "#ffc107"

        try:
            current_lang = get_language()
        except Exception:
            current_lang = "CN"

        if current_lang != "EN":
            current_lang = "CN"

        if current_lang == "CN":
            css_lang_en = "display: none;"
            css_lang_zh = "display: inline;"
            btn_text = "Switch to English"
        else:
            css_lang_en = "display: inline;"
            css_lang_zh = "display: none;"
            btn_text = "切换到中文"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Advanced Medical Analysis Report - {patient_id}</title>
            <style>
                :root {{
                    --primary-color: #0056b3;
                    --secondary-color: #f8f9fa;
                    --accent-color: {status_color};
                    --text-color: #333;
                    --border-color: #dee2e6;
                }}
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: var(--text-color); max-width: 1200px; margin: 0 auto; padding: 20px; background: #f4f7f6; }}
                .header {{
                    position: relative;
                    overflow: hidden;
                    background: linear-gradient(135deg, rgba(11, 18, 32, 0.94), rgba(0, 68, 148, 0.92));
                    color: rgba(255, 255, 255, 0.92);
                    padding: 30px;
                    border-radius: 12px 12px 0 0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    box-shadow: 0 12px 28px rgba(0, 0, 0, 0.18);
                    border: 1px solid rgba(255, 255, 255, 0.12);
                }}
                .header > * {{ position: relative; z-index: 1; }}
                .header.fx-silk::before,
                .header.fx-silk::after {{
                    content: "";
                    position: absolute;
                    inset: 0;
                    pointer-events: none;
                    z-index: 0;
                }}
                .header.fx-silk::before {{
                    opacity: 0.9;
                    background:
                      radial-gradient(360px 220px at 25% 25%, rgba(103, 209, 255, 0.22), transparent 60%),
                      radial-gradient(360px 220px at 75% 25%, rgba(155, 123, 255, 0.18), transparent 60%),
                      radial-gradient(420px 260px at 50% 120%, rgba(80, 255, 196, 0.14), transparent 60%);
                    filter: blur(18px) saturate(1.1);
                }}
                .header.fx-silk::after {{
                    opacity: 0.35;
                    background-image:
                      linear-gradient(120deg, rgba(255, 255, 255, 0.06), transparent 55%),
                      linear-gradient(45deg, rgba(255, 255, 255, 0.05), transparent 60%),
                      linear-gradient(-60deg, rgba(255, 255, 255, 0.04), transparent 65%);
                    animation: silk 7.4s ease-in-out infinite;
                }}
                @keyframes silk {{
                    0% {{ transform: translate3d(-8%, 0, 0); }}
                    50% {{ transform: translate3d(8%, 0, 0); }}
                    100% {{ transform: translate3d(-8%, 0, 0); }}
                }}
                .section {{ background: white; padding: 30px; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 2px 15px rgba(0,0,0,0.05); border-top: 4px solid var(--primary-color); }}
                h1 {{ margin: 0; font-size: 28px; font-weight: 600; letter-spacing: 0.5px; }}
                h2 {{ color: var(--primary-color); border-bottom: 2px solid var(--secondary-color); padding-bottom: 12px; margin-top: 0; font-size: 22px; display: flex; align-items: center; }}
                h2::before {{ content: ''; display: inline-block; width: 8px; height: 24px; background: var(--primary-color); margin-right: 12px; border-radius: 4px; }}
                h3 {{ color: #555; margin-top: 25px; font-size: 18px; font-weight: 600; }}
                h4 {{ font-size: 16px; margin-bottom: 10px; }}
                table {{ width: 100%; border-collapse: separate; border-spacing: 0; margin: 20px 0; border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; }}
                th, td {{ padding: 15px; text-align: left; border-bottom: 1px solid var(--border-color); }}
                th {{ background: var(--secondary-color); color: #495057; font-weight: 600; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px; }}
                tr:last-child td {{ border-bottom: none; }}
                tr:hover {{ background-color: #f8f9fa; }}
                
                .risk-High {{ color: #dc3545; font-weight: 700; }}
                .risk-Moderate {{ color: #ffc107; font-weight: 700; }}
                .risk-Low {{ color: #28a745; font-weight: 700; }}
                
                .recommendation-box {{ background: #eeffff; padding: 20px; border-left: 5px solid #17a2b8; margin-top: 15px; border-radius: 0 8px 8px 0; }}
                .surgical-box {{ background: #fff5f5; padding: 20px; border-left: 5px solid #dc3545; margin-top: 15px; border-radius: 0 8px 8px 0; }}
                .info-box {{ background: #e2e3e5; padding: 15px; border-radius: 6px; font-size: 14px; margin-top: 15px; border: 1px solid #d6d8db; }}
                
                .footer {{ text-align: center; color: #888; font-size: 12px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; }}
                .grid-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px; }}
                
                .stat-card {{ background: var(--secondary-color); padding: 20px; border-radius: 8px; border: 1px solid var(--border-color); }}
                .stat-value {{ font-size: 24px; font-weight: 700; color: var(--primary-color); }}
                .stat-label {{ font-size: 13px; color: #6c757d; text-transform: uppercase; margin-top: 5px; }}
                
                /* Metrics Bar */
                .metric-bar {{ height: 8px; background: #e9ecef; border-radius: 4px; margin-top: 8px; overflow: hidden; }}
                .metric-fill {{ height: 100%; border-radius: 4px; transition: width 0.5s ease; }}
                
                /* Language Toggle Styles */
                .lang-en {{ {css_lang_en} }}
                .lang-zh {{ {css_lang_zh} }}
                .lang-toggle-btn {{
                    background: rgba(255, 255, 255, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.4);
                    color: white;
                    padding: 8px 20px;
                    border-radius: 30px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 600;
                    transition: all 0.2s;
                    backdrop-filter: blur(5px);
                }}
                .lang-toggle-btn:hover {{ background: rgba(255, 255, 255, 0.3); transform: translateY(-1px); }}
                
                .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; color: white; }}
                .badge-high {{ background-color: #dc3545; }}
                .badge-mod {{ background-color: #ffc107; color: #333; }}
                .badge-low {{ background-color: #28a745; }}
                
                .detail-text {{ font-size: 14px; color: #555; margin-bottom: 10px; }}
                .term-en {{ font-weight: 600; color: #333; }}
            </style>
            <script>
                function toggleLanguage() {{
                    var enElements = document.querySelectorAll('.lang-en');
                    var zhElements = document.querySelectorAll('.lang-zh');
                    var btn = document.getElementById('langBtn');
                    
                    var enDisplay = window.getComputedStyle(enElements[0]).display;
                    var isEnVisible = enDisplay !== 'none';
                    
                    if (isEnVisible) {{
                        enElements.forEach(el => el.style.display = 'none');
                        zhElements.forEach(el => el.style.display = 'inline');
                        btn.textContent = 'Switch to English';
                    }} else {{
                        enElements.forEach(el => el.style.display = 'inline');
                        zhElements.forEach(el => el.style.display = 'none');
                        btn.textContent = '切换到中文';
                    }}
                }}
            </script>
        </head>
        <body>
            <div class="header fx-silk">
                <div>
                    <h1>
                        <span class="lang-en">Advanced Medical Analysis Report</span>
                        <span class="lang-zh">高级医学影像分析报告</span>
                    </h1>
                    <div style="font-size: 14px; opacity: 0.9; margin-top: 5px;">
                        <span class="lang-en">AI-Assisted Surgical Planning & Diagnostic System</span>
                        <span class="lang-zh">AI辅助手术规划与诊断系统</span>
                    </div>
                    <div style="font-size: 12px; opacity: 0.7; margin-top: 5px;">
                        <span class="lang-en">Institution: LPDP-RiR Advanced Medical Center</span>
                        <span class="lang-zh">机构: LPDP-RiR 高级医学中心</span>
                    </div>
                </div>
                <div style="text-align: right;">
                    <button id="langBtn" class="lang-toggle-btn" onclick="toggleLanguage()">{btn_text}</button>
                    <div style="margin-top: 15px; font-size: 14px;">
                        <span class="lang-en">Patient ID:</span><span class="lang-zh">患者ID:</span> <strong>{patient_id}</strong><br>
                        <span class="lang-en">Date:</span><span class="lang-zh">报告日期:</span> {datetime.now().strftime("%Y-%m-%d %H:%M")}
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>
                    <span class="lang-en">1. Clinical Executive Summary</span>
                    <span class="lang-zh">1. 临床执行摘要</span>
                </h2>
                
                <div style="margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 15px;">
                     <h4 style="color: #495057;">
                        <span class="lang-en">Study Protocol & Methodology</span>
                        <span class="lang-zh">检查方案与方法学</span>
                    </h4>
                    <p class="detail-text">
                        <span class="lang-en">
                            This report is based on High-Resolution Computed Tomography (HRCT) data. 
                            The analysis utilizes <strong>Deep Learning</strong> for automated lesion detection and segmentation, 
                            combined with <strong>Geometric Ray-Casting</strong> for 3D surgical path planning.
                            The system evaluates tissue density (Hounsfield Units) and morphology to assess malignancy risk.
                        </span>
                        <span class="lang-zh">
                            本报告基于高分辨率计算机断层扫描 (HRCT) 数据。
                            分析采用 <strong>深度学习</strong> 进行自动病灶检测与分割，
                            结合 <strong>几何光线投射算法</strong> 进行3D手术路径规划。
                            系统通过评估组织密度（亨氏单位 HU）和形态学特征来评估恶性风险。
                        </span>
                    </p>
                </div>

                <div class="grid-container">
                    <div class="stat-card">
                        <div class="stat-value">{num_lesions}</div>
                        <div class="stat-label">
                            <span class="lang-en">Detected Lesions</span>
                            <span class="lang-zh">检出病灶数</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="color: {status_color}">{max_risk}</div>
                        <div class="stat-label">
                            <span class="lang-en">Highest Risk Level</span>
                            <span class="lang-zh">最高风险等级</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{len(surgical_plans)}</div>
                        <div class="stat-label">
                            <span class="lang-en">Surgical Candidates</span>
                            <span class="lang-zh">手术候选病灶</span>
                        </div>
                    </div>
                </div>
                
                <div class="info-box">
                    <strong>
                        <span class="lang-en">Automated Clinical Assessment:</span>
                        <span class="lang-zh">自动临床评估结论:</span>
                    </strong>
                    <div style="margin-top: 5px;">
                        <span class="lang-en">
                            The comprehensive analysis indicates a <strong>{max_risk}</strong> risk profile for this patient. 
                            {f"Immediate attention is required for {len(surgical_plans)} lesion(s) identified as candidates for surgical intervention." if surgical_plans else "Currently, no immediate surgical targets have been identified, but regular monitoring is advised."}
                            The risk stratification is based on lesion size, density, and growth patterns.
                        </span>
                        <span class="lang-zh">
                            综合分析显示该患者的总体风险概况为 <strong>{max_risk}</strong>。
                            {f"需立即关注 {len(surgical_plans)} 个被识别为手术干预候选的病灶。" if surgical_plans else "目前未发现需立即手术的目标，但建议定期监测。"}
                            风险分层基于病灶大小、密度和生长模式。
                        </span>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>
                    <span class="lang-en">2. Detailed Radiological Findings</span>
                    <span class="lang-zh">2. 详细影像学发现</span>
                </h2>
                <p class="detail-text">
                    <span class="lang-en">
                        The following table details the quantitative metrics for each detected lesion. 
                        Coordinates are provided in (Z, Y, X) voxel space. 
                        Density is measured in Hounsfield Units (HU).
                    </span>
                    <span class="lang-zh">
                        下表详细列出了每个检出病灶的定量指标。
                        坐标以 (Z, Y, X) 体素空间提供。
                        密度以亨氏单位 (HU) 测量。
                    </span>
                </p>
                
                <div style="margin-bottom: 20px; padding: 10px; background: #e9ecef; border-radius: 4px; display: flex; justify-content: space-around; text-align: center;">
                    <div>
                        <div style="font-size: 24px; font-weight: bold; color: #0056b3;">{len(lesion_analyses)}</div>
                        <div style="font-size: 12px; color: #666;">
                            <span class="lang-en">Total Lesions</span>
                            <span class="lang-zh">病灶总数</span>
                        </div>
                    </div>
                    <div>
                        <div style="font-size: 24px; font-weight: bold; color: #dc3545;">{sum(1 for l in lesion_analyses if "High" in l["risk_level"] or "Moderate" in l["risk_level"])}</div>
                        <div style="font-size: 12px; color: #666;">
                            <span class="lang-en">Actionable Targets</span>
                            <span class="lang-zh">需处理目标</span>
                        </div>
                    </div>
                    <div>
                        <div style="font-size: 24px; font-weight: bold; color: #28a745;">{max((l['diameter_mm'] for l in lesion_analyses), default=0):.1f} mm</div>
                        <div style="font-size: 12px; color: #666;">
                            <span class="lang-en">Max Diameter</span>
                            <span class="lang-zh">最大直径</span>
                        </div>
                    </div>
                </div>

                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>
                                <span class="lang-en">Location (Z, Y, X)</span>
                                <span class="lang-zh">位置 (Z, Y, X)</span>
                            </th>
                            <th>
                                <span class="lang-en">Dimensions</span>
                                <span class="lang-zh">维度指标</span>
                            </th>
                            <th>
                                <span class="lang-en">Density Characteristics</span>
                                <span class="lang-zh">密度特征</span>
                            </th>
                            <th>
                                <span class="lang-en">Classification</span>
                                <span class="lang-zh">分类诊断</span>
                            </th>
                            <th>
                                <span class="lang-en">Risk Assessment</span>
                                <span class="lang-zh">风险评估</span>
                            </th>
                            <th>
                                <span class="lang-en">Judgment Basis</span>
                                <span class="lang-zh">判断依据</span>
                            </th>
                        </tr>
                    </thead>
                    <tbody>
        """

        for i, l in enumerate(lesion_analyses):
            pos = l["pos"]
            risk_class = l["risk_level"].split(" ")[0]

            def split_bilingual(text):
                if "(" in text and ")" in text:
                    parts = text.split("(")
                    en = parts[0].strip()
                    zh = parts[1].replace(")", "").strip()
                    return en, zh
                return text, text

            risk_en, risk_zh = split_bilingual(l["risk_level"])
            density_en, density_zh = split_bilingual(l["density_type"])
            size_en, size_zh = split_bilingual(l["size_category"])

            vol_mm3 = l.get("volume_mm3", 0)
            mean_hu = l.get("mean_hu", 0)
            min_hu = l.get("min_hu", 0)
            max_hu = l.get("max_hu", 0)

            if "High" in l["risk_level"]:
                basis_en = f"Diameter > 6mm ({l['diameter_mm']:.1f}mm) with density variation ({mean_hu:.0f} HU) suggests malignancy."
                basis_zh = f"直径 > 6mm ({l['diameter_mm']:.1f}mm) 且伴有密度变化 ({mean_hu:.0f} HU)，提示恶性风险。"
            elif "Moderate" in l["risk_level"]:
                basis_en = f"Indeterminate size ({l['diameter_mm']:.1f}mm) or density ({mean_hu:.0f} HU). Follow-up required."
                basis_zh = f"尺寸 ({l['diameter_mm']:.1f}mm) 或密度 ({mean_hu:.0f} HU) 特征不确定，需随访。"
            else:
                basis_en = "Small size and stable density characteristics suggest benign nature."
                basis_zh = "尺寸较小且密度特征稳定，提示良性。"

            html_content += f"""
                        <tr>
                            <td><strong>#{i+1}</strong></td>
                            <td style="font-family: monospace;">{pos}</td>
                            <td>
                                <div>
                                    <strong><span class="lang-en">Diameter:</span><span class="lang-zh">直径:</span></strong> 
                                    {l['diameter_mm']:.1f} mm
                                </div>
                                <div style="font-size: 12px; color: #666;">
                                    <strong><span class="lang-en">Volume:</span><span class="lang-zh">体积:</span></strong> 
                                    {vol_mm3:.1f} mm³
                                </div>
                            </td>
                            <td>
                                <div>
                                    <span class="lang-en">{density_en}</span>
                                    <span class="lang-zh">{density_zh}</span>
                                </div>
                                <div style="font-size: 12px; color: #666;">
                                    <span class="lang-en">Avg:</span><span class="lang-zh">平均:</span> {mean_hu:.1f} HU<br>
                                    <span class="lang-en">Range:</span><span class="lang-zh">范围:</span> [{min_hu:.0f}, {max_hu:.0f}]
                                </div>
                            </td>
                            <td>
                                <span class="badge" style="background-color: #6c757d;">
                                    <span class="lang-en">{size_en}</span>
                                    <span class="lang-zh">{size_zh}</span>
                                </span>
                            </td>
                            <td>
                                <span class="risk-{risk_class}">
                                    <span class="lang-en">{risk_en}</span>
                                    <span class="lang-zh">{risk_zh}</span>
                                </span>
                            </td>
                            <td>
                                <span class="detail-text" style="font-size: 12px;">
                                    <span class="lang-en">{basis_en}</span>
                                    <span class="lang-zh">{basis_zh}</span>
                                </span>
                            </td>
                        </tr>
            """

        html_content += """
                    </tbody>
                </table>
            </div>

            <div class="section">
                <h2>
                    <span class="lang-en">3. Surgical Planning & Treatment Recommendations</span>
                    <span class="lang-zh">3. 手术规划与治疗建议</span>
                </h2>
                <div style="background: #fff3cd; padding: 15px; border-radius: 6px; margin-bottom: 20px; font-size: 14px; border: 1px solid #ffeeba;">
                    <strong><span class="lang-en">Planning Strategy:</span><span class="lang-zh">规划策略:</span></strong>
                    <span class="lang-en">
                        Surgical interventions are prioritized for High and Moderate risk lesions. 
                        Path planning optimizes for the shortest trajectory while strictly avoiding high-density structures (Bone > 300 HU) and major vasculature.
                    </span>
                    <span class="lang-zh">
                        对于高风险及中风险病灶，优先推荐手术干预。
                        路径规划在优化最短轨迹的同时，严格避让高密度结构（骨骼 > 300 HU）及主要血管。
                    </span>
                </div>
        """

        for i, l in enumerate(lesion_analyses):
            rec = l["recommendation"]
            risk_class = l["risk_level"].split(" ")[0]

            rec_en, rec_zh = l["recommendation"], l["recommendation"]
            if "(" in rec and ")" in rec:
                parts = rec.split("(")
                rec_en = parts[0].strip()
                rec_zh = parts[1].replace(")", "").strip()

            risk_en, risk_zh = l["risk_level"], l["risk_level"]
            if "(" in risk_en:
                parts = risk_en.split("(")
                risk_en = parts[0].strip()
                risk_zh = parts[1].replace(")", "").strip()

            html_content += f"""
                <div style="margin-bottom: 30px; border: 1px solid #eee; border-radius: 8px; overflow: hidden;">
                    <div style="background: #f8f9fa; padding: 15px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="margin: 0;">
                            <span class="lang-en">Target Lesion #{i+1}</span>
                            <span class="lang-zh">目标病灶 #{i+1}</span>
                        </h3>
                        <span class="risk-{risk_class}">
                             <span class="lang-en">{risk_en}</span>
                             <span class="lang-zh">{risk_zh}</span>
                        </span>
                    </div>
                    <div style="padding: 20px;">
                        <div class="recommendation-box" style="margin-top: 0; margin-bottom: 15px;">
                            <strong>
                                <span class="lang-en">Clinical Recommendation:</span>
                                <span class="lang-zh">临床建议:</span>
                            </strong> 
                            <span class="lang-en">{rec_en}</span>
                            <span class="lang-zh">{rec_zh}</span>
                        </div>
            """

            if "High" in risk_class or "Moderate" in risk_class:
                plan = next((p for p in surgical_plans if p["id"] == i + 1), None)
                if plan:
                    entry = plan["entry"]
                    risk_score = plan["risk"]
                    metrics = plan.get("metrics", {})
                    depth = metrics.get("depth_mm", 0)
                    angle_ax = metrics.get("angle_axial", 0)
                    angle_vt = metrics.get("angle_vertical", 0)

                    risk_percent = min(100, (risk_score / 50.0) * 100)

                    html_content += f"""
                    <div class="surgical-box">
                        <h4 style="margin-top: 0; color: #dc3545; border-bottom: 1px solid #f5c6cb; padding-bottom: 10px;">
                            <span class="lang-en">⚡ Surgical Path Analysis & Pre-operative Planning</span>
                            <span class="lang-zh">⚡ 手术路径分析与术前规划</span>
                        </h4>
                        
                        <p class="detail-text" style="font-size: 13px;">
                            <span class="lang-en">
                                The following analysis provides a computed optimal trajectory for percutaneous intervention. 
                                Metrics are calculated relative to the patient's axial plane.
                            </span>
                            <span class="lang-zh">
                                以下分析提供了经皮介入治疗的计算最佳轨迹。
                                指标是相对于患者的轴状位平面计算的。
                            </span>
                        </p>

                        <div class="grid-container" style="grid-template-columns: 1fr 1fr;">
                            <div>
                                <strong>
                                    <span class="lang-en">Optimal Entry Point (Z,Y,X):</span>
                                    <span class="lang-zh">最佳穿刺点 (Z,Y,X):</span>
                                </strong><br>
                                <span style="font-family: monospace; background: white; padding: 2px 5px; border-radius: 4px;">{entry}</span>
                                <div style="font-size: 11px; color: #666; margin-top: 2px;">
                                    <span class="lang-en">Skin surface coordinate</span>
                                    <span class="lang-zh">皮肤表面坐标</span>
                                </div>
                            </div>
                            <div>
                                <strong>
                                    <span class="lang-en">Target Location (Z,Y,X):</span>
                                    <span class="lang-zh">目标靶点 (Z,Y,X):</span>
                                </strong><br>
                                <span style="font-family: monospace; background: white; padding: 2px 5px; border-radius: 4px;">{l['pos']}</span>
                                <div style="font-size: 11px; color: #666; margin-top: 2px;">
                                    <span class="lang-en">Lesion center of mass</span>
                                    <span class="lang-zh">病灶质心</span>
                                </div>
                            </div>
                        </div>

                        <div style="margin-top: 15px; padding: 10px; background-color: #f0f8ff; border-left: 3px solid #0056b3; border-radius: 4px;">
                            <strong>
                                <span class="lang-en">Path Description:</span>
                                <span class="lang-zh">路径描述:</span>
                            </strong>
                            <p style="margin: 5px 0 0 0; font-size: 13px; color: #333;">
                                <span class="lang-en">{plan.get('description', {}).get('en', 'No description available.')}</span>
                                <span class="lang-zh">{plan.get('description', {}).get('zh', '暂无描述。')}</span>
                            </p>
                        </div>

                        <div style="margin-top: 15px;">
                            <strong>
                                <span class="lang-en">Path Metrics:</span>
                                <span class="lang-zh">路径指标:</span>
                            </strong>
                            <ul style="margin-top: 5px; color: #555;">
                                <li>
                                    <span class="lang-en">Trajectory Depth:</span>
                                    <span class="lang-zh">轨迹深度:</span> 
                                    <strong>{depth:.1f} mm</strong>
                                    <span style="font-size: 12px; color: #888;"> (Skin to Target distance)</span>
                                </li>
                                <li>
                                    <span class="lang-en">Entry Angle (Axial):</span>
                                    <span class="lang-zh">穿刺角度 (轴位):</span> 
                                    {angle_ax:.1f}°
                                    <span style="font-size: 12px; color: #888;"> (0°=Right, 90°=Anterior)</span>
                                </li>
                                <li>
                                    <span class="lang-en">Entry Angle (Vertical):</span>
                                    <span class="lang-zh">穿刺角度 (垂直):</span> 
                                    {angle_vt:.1f}°
                                    <span style="font-size: 12px; color: #888;"> (Elevation from XY plane)</span>
                                </li>
                            </ul>
                        </div>

                        <div style="margin-top: 15px; background: white; padding: 10px; border-radius: 4px; border: 1px solid #eee;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <strong>
                                    <span class="lang-en">Path Risk Score:</span>
                                    <span class="lang-zh">路径风险评分:</span>
                                    {risk_score:.1f}
                                </strong>
                                <span style="color: #666; font-size: 12px;">
                                    <span class="lang-en">Lower is Safer</span>
                                    <span class="lang-zh">越低越安全</span>
                                </span>
                            </div>
                            <div class="metric-bar">
                                <div class="metric-fill" style="width: {risk_percent}%; background: {'#28a745' if risk_score < 20 else '#ffc107' if risk_score < 50 else '#dc3545'};"></div>
                            </div>
                            <div style="font-size: 11px; color: #888; margin-top: 5px;">
                                <span class="lang-en">Avoidance Logic: Bone (>300HU), Major Vessels (>100HU), Air (< -600HU)</span>
                                <span class="lang-zh">避让逻辑：骨骼 (>300HU), 大血管 (>100HU), 空气 (< -600HU)</span>
                            </div>
                        </div>

                        <details style="margin-top: 15px;">
                            <summary style="cursor: pointer; color: #0056b3; font-size: 13px;">
                                <span class="lang-en">View Detailed Trajectory Coordinates</span>
                                <span class="lang-zh">查看详细轨迹坐标</span>
                            </summary>
                            <code style="display:block; padding:10px; background:white; border:1px solid #ddd; margin-top:5px; max-height: 100px; overflow-y: auto; font-size: 12px;">
                                {plan.get('path', 'N/A')}
                            </code>
                        </details>

                        <div style="margin-top: 15px; background: #fff3cd; padding: 10px; border-radius: 4px; border: 1px solid #ffeeba;">
                            <strong>
                                <span class="lang-en">Surgical Contingency Protocol:</span>
                                <span class="lang-zh">手术应急预案:</span>
                            </strong>
                            <ul style="margin: 5px 0 0 20px; font-size: 13px; color: #856404;">
                                <li>
                                    <span class="lang-en">If needle deflection > 2mm observed: Retract to subcutaneous layer and re-align using coaxial technique.</span>
                                    <span class="lang-zh">如果观察到穿刺针偏转 > 2mm：退至皮下层并使用同轴技术重新对准。</span>
                                </li>
                                <li>
                                     <span class="lang-en">If respiratory motion artifact interferes: Switch to respiratory-gated acquisition mode.</span>
                                     <span class="lang-zh">如果呼吸运动伪影干扰：切换至呼吸门控采集模式。</span>
                                </li>
                                {f"<li><span class='lang-en'>High Risk Warning: Proximity to critical structures detected. If patient reports radiating pain, STOP immediately.</span><span class='lang-zh'>高风险警告：检测到临近关键结构。如果患者报告放射性疼痛，立即停止。</span></li>" if risk_score > 30 else ""}
                            </ul>
                        </div>
                    </div>
                    """

            treatment_plan = l.get("treatment_plan")
            clin_surgical_path = l.get("surgical_path")
            stage_info = l.get("stage_info")

            if treatment_plan or clin_surgical_path:
                html_content += f"""
                    <div style="background: #f3f0ff; padding: 20px; border-left: 5px solid #6f42c1; margin-top: 15px; border-radius: 0 8px 8px 0;">
                        <h4 style="margin-top: 0; color: #6f42c1; border-bottom: 1px solid #e0d8f0; padding-bottom: 10px;">
                            <span class="lang-en">⚕️ Oncological Treatment Strategy (NCCN/ESMO Aligned)</span>
                            <span class="lang-zh">⚕️ 肿瘤治疗策略 (对标 NCCN/ESMO)</span>
                        </h4>
                """

                if stage_info:
                    t_stage = stage_info.get("t_stage", "Tx")
                    c_stage = stage_info.get("clinical_stage_group", "Unknown")
                    html_content += f"""
                        <div style="margin-bottom: 15px;">
                             <strong>
                                <span class="lang-en">Estimated Staging:</span>
                                <span class="lang-zh">预估分期:</span>
                             </strong>
                             <span style="background: #6f42c1; color: white; padding: 2px 8px; border-radius: 4px; font-size: 13px; font-weight: bold;">{c_stage} (T: {t_stage})</span>
                        </div>
                    """

                if treatment_plan:
                    html_content += """
                        <table style="width: 100%; font-size: 13px; background: white; margin-bottom: 15px;">
                            <tr style="background: #e0d8f0;">
                                <th style="padding: 8px;"><span class="lang-en">Protocol</span><span class="lang-zh">方案</span></th>
                                <th style="padding: 8px;"><span class="lang-en">Type</span><span class="lang-zh">类型</span></th>
                                <th style="padding: 8px;"><span class="lang-en">Rec. Score</span><span class="lang-zh">推荐分</span></th>
                            </tr>
                    """
                    for idx, tp in enumerate(treatment_plan):
                        if idx >= 3:
                            break

                        weight = tp.get("weight", 0)
                        score_bar = f'<div style="width: {min(100, weight)}px; height: 6px; background: #6f42c1; border-radius: 3px;"></div>'

                        protocol_name = f"""
                            <div><span class="lang-en"><b>{tp.get('name_en')}</b></span><span class="lang-zh"><b>{tp.get('name_zh')}</b></span></div>
                            <div style="color: #666; font-size: 11px; margin-top: 2px;">
                                <span class="lang-en">{tp.get('desc_en')}</span><span class="lang-zh">{tp.get('desc_zh')}</span>
                            </div>
                        """

                        if "components" in tp:
                            comps = ", ".join(tp["components"])
                            protocol_name += f'<div style="color: #d63384; font-size: 11px;">+ {comps}</div>'

                        html_content += f"""
                            <tr>
                                <td style="padding: 8px; border-bottom: 1px solid #eee;">{protocol_name}</td>
                                <td style="padding: 8px; border-bottom: 1px solid #eee;">{tp.get('type', 'Standard')}</td>
                                <td style="padding: 8px; border-bottom: 1px solid #eee;">
                                    <div style="font-weight: bold; color: #6f42c1;">{weight}</div>
                                    {score_bar}
                                </td>
                            </tr>
                        """
                    html_content += "</table>"

                if clin_surgical_path:
                    approaches = clin_surgical_path.get("approach", [])
                    resections = clin_surgical_path.get("resection", [])

                    if approaches:
                        top_approach = approaches[0]
                        html_content += f"""
                             <div style="margin-top: 10px;">
                                <strong><span class="lang-en">Recommended Surgical Approach:</span><span class="lang-zh">推荐手术入路:</span></strong>
                                <ul style="margin: 5px 0 0 20px; font-size: 13px;">
                                    <li>
                                        <span class="lang-en">{top_approach.get('name_en')}</span>
                                        <span class="lang-zh">{top_approach.get('name_zh')}</span>
                                        <span style="color: #28a745; font-size: 11px;"> (Invasiveness: {top_approach.get('invasiveness')})</span>
                                    </li>
                                </ul>
                             </div>
                        """

                    if resections:
                        top_resection = resections[0]
                        html_content += f"""
                             <div style="margin-top: 10px;">
                                <strong><span class="lang-en">Extent of Resection:</span><span class="lang-zh">切除范围:</span></strong>
                                <span style="font-size: 13px;">
                                    <span class="lang-en">{top_resection.get('name_en')}</span>
                                    <span class="lang-zh">{top_resection.get('name_zh')}</span>
                                </span>
                             </div>
                        """

                html_content += "</div>"

            html_content += """
                    </div>
                </div>
            """

        html_content += """
            </div>
        """

        tnm_rows_html = ""
        follow_rows_html = ""

        for l in lesion_analyses:
            stage_info = l.get("stage_info")
            if stage_info:
                t_stage = stage_info.get("t_stage", "Tx")
                c_stage = stage_info.get("clinical_stage_group", "Unknown")
                lung_rads = l.get("lung_rads_score", "")
                tnm_rows_html += f"""
                            <tr>
                                <td>#{l.get('id', '')}</td>
                                <td>{lung_rads}</td>
                                <td>{t_stage}</td>
                                <td>{c_stage}</td>
                                <td>{l.get('risk_level', '')}</td>
                            </tr>
                """

            rec = l.get("recommendation")
            if rec:
                follow_rows_html += f"""
                            <tr>
                                <td>#{l.get('id', '')}</td>
                                <td>{l.get('risk_level', '')}</td>
                                <td>{rec}</td>
                            </tr>
                """

        if tnm_rows_html or follow_rows_html:
            html_content += f"""
            <div class="section">
                <h2>
                    <span class="lang-en">4. TNM Staging & Follow-up Plan</span>
                    <span class="lang-zh">4. TNM 分期与随访建议</span>
                </h2>
            """

            if tnm_rows_html:
                html_content += f"""
                <h3 style="margin-top: 10px;">
                    <span class="lang-en">TNM Staging Table</span>
                    <span class="lang-zh">TNM 分期表</span>
                </h3>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Lung-RADS</th>
                            <th>T</th>
                            <th>
                                <span class="lang-en">Clinical Stage</span>
                                <span class="lang-zh">临床分期</span>
                            </th>
                            <th>
                                <span class="lang-en">Risk</span>
                                <span class="lang-zh">风险等级</span>
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {tnm_rows_html}
                    </tbody>
                </table>
                """

            if follow_rows_html:
                html_content += f"""
                <h3 style="margin-top: 20px;">
                    <span class="lang-en">Follow-up Recommendation Table</span>
                    <span class="lang-zh">随访建议表</span>
                </h3>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>
                                <span class="lang-en">Risk Level</span>
                                <span class="lang-zh">风险等级</span>
                            </th>
                            <th>
                                <span class="lang-en">Follow-up Plan</span>
                                <span class="lang-zh">随访与管理建议</span>
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {follow_rows_html}
                    </tbody>
                </table>
                """

            html_content += """
            </div>
            """

        if images:
            html_content += """
            <div class="section">
                <h2>
                    <span class="lang-en">5. Diagnostic Imaging Preview</span>
                    <span class="lang-zh">5. 诊断影像预览</span>
                </h2>
                <p class="detail-text">
                    <span class="lang-en">
                        Selected key slices demonstrating the detected lesions. 
                        Red contours indicate the AI-segmented boundaries.
                    </span>
                    <span class="lang-zh">
                        展示检出病灶的关键切片。
                        红色轮廓表示AI分割的边界。
                    </span>
                </p>
                <div style="background: #f8f9fa; padding: 10px; border-radius: 4px; margin-bottom: 15px; font-size: 13px; color: #555;">
                    <strong><span class="lang-en">Interpretation Guide:</span><span class="lang-zh">阅片指南:</span></strong>
                    <ul style="margin: 5px 0 0 20px;">
                        <li>
                            <span class="lang-en">Images are presented in axial view. Green crosshairs mark the lesion center.</span>
                            <span class="lang-zh">图像以轴位展示。绿色十字准线标记病灶中心。</span>
                        </li>
                        <li>
                             <span class="lang-en">Please correlate with 3D volume rendering for full spatial assessment.</span>
                             <span class="lang-zh">请结合3D体渲染进行全面的空间评估。</span>
                        </li>
                        <li>
                             <span class="lang-en">Scale bars (if present) indicate 10mm increments.</span>
                             <span class="lang-zh">比例尺（如有）表示 10mm 增量。</span>
                        </li>
                    </ul>
                </div>
                <div class="grid-container" style="grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));">
            """
            for im in images:
                try:
                    path_obj = Path(im)
                    if path_obj.exists():
                        b = path_obj.read_bytes()
                        b64 = base64.b64encode(b).decode("ascii")
                        src = "data:image/png;base64," + b64

                        stem = path_obj.stem
                        slice_label = ""
                        for part in stem.split("_"):
                            if part.isdigit():
                                try:
                                    slice_label = str(int(part))
                                except ValueError:
                                    slice_label = part
                                break

                        caption = ""
                        if slice_label:
                            caption = (
                                f'<div style="font-size:12px;color:#555;margin-bottom:4px;">'
                                f'<span class="lang-zh">切片编号: {slice_label}</span> '
                                f'<span class="lang-en">Slice index: {slice_label}</span>'
                                f"</div>"
                            )

                        html_content += (
                            "<div>"
                            + caption
                            + f'<img src="{src}" style="width:100%;height:auto;border:1px solid #ddd; border-radius: 4px;">'
                            + "</div>"
                        )
                except Exception:
                    pass
            html_content += """
                </div>
            </div>
            """

        html_content += """
            <div class="section" style="border-top: 4px solid #6c757d;">
                <h2>
                    <span class="lang-en">6. Disclaimer & Legal Notice</span>
                    <span class="lang-zh">6. 免责声明与法律声明</span>
                </h2>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 6px;">
                    <p style="font-size: 13px; color: #666; text-align: justify; margin: 0;">
                        <span class="lang-en">
                            This advanced medical analysis report is generated by an AI-assisted diagnostic system (Modules: LesionClassifier, SurgicalPlanner). 
                            While the system utilizes state-of-the-art algorithms for 3D reconstruction and path planning, it is intended <strong>strictly for reference and research purposes only</strong>. 
                            It does NOT constitute a definitive medical diagnosis or a final surgical instruction. 
                            Any clinical decision, including surgical intervention, biopsy, or treatment planning, must be validated by qualified medical professionals (radiologists/surgeons). 
                            The generated surgical paths are mathematical approximations and may not account for real-time intraoperative deformations.
                            The developers assume no liability for actions taken based on this report.
                        </span>
                        <span class="lang-zh">
                            本高级医学分析报告由AI辅助诊断系统（模块：病灶分类器、手术规划器）生成。
                            尽管系统采用了先进的3D重建和路径规划算法，但其结果<strong>仅供参考和研究目的</strong>。
                            本报告不构成最终医学诊断或最终手术指令。
                            任何临床决策（包括手术干预、活检或治疗方案制定）必须由具备资质的医疗专业人员（放射科医生/外科医生）进行验证。
                            生成的“手术路径”为数学近似值，可能无法完全涵盖术中实时形变等复杂情况。
                            开发者不对基于本报告采取的任何行动承担责任。
                        </span>
                    </p>
                </div>
            </div>
            
            <div class="footer">
                &copy; 2026 LPDP-RiR Advanced Medical Analysis System. All Rights Reserved.<br>
            </div>
        </body>
        </html>
        """

        html_path = os.path.join(self.output_dir, output_filename)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        pdf_path = os.path.splitext(html_path)[0] + ".pdf"

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import (
                SimpleDocTemplate,
                Paragraph,
                Spacer,
                Table,
                TableStyle,
                Image,
            )
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            doc = SimpleDocTemplate(
                pdf_path,
                pagesize=A4,
                rightMargin=36,
                leftMargin=36,
                topMargin=36,
                bottomMargin=36,
            )

            styles = getSampleStyleSheet()

            base_font = "Helvetica"
            font_path = "C:/Windows/Fonts/msyh.ttc"
            if Path(font_path).exists():
                try:
                    pdfmetrics.registerFont(TTFont("MSYH", font_path))
                    base_font = "MSYH"
                except Exception:
                    pass

            styles.add(
                ParagraphStyle(
                    name="TitleCNEN",
                    parent=styles["Title"],
                    fontName=base_font,
                    fontSize=18,
                    leading=22,
                )
            )
            styles.add(
                ParagraphStyle(
                    name="Heading",
                    parent=styles["Heading2"],
                    fontName=base_font,
                    fontSize=13,
                    leading=16,
                    spaceBefore=12,
                    spaceAfter=6,
                )
            )
            styles.add(
                ParagraphStyle(
                    name="Body",
                    parent=styles["Normal"],
                    fontName=base_font,
                    fontSize=10,
                    leading=14,
                    wordWrap="CJK",
                )
            )

            story = []

            title_text = "高级医学影像分析报告 / Advanced Medical Analysis Report"
            story.append(Paragraph(title_text, styles["TitleCNEN"]))
            story.append(Spacer(1, 12))

            meta_lines = [
                f"患者ID / Patient ID: {patient_id}",
                "报告日期 / Report Date: " + datetime.now().strftime("%Y-%m-%d %H:%M"),
                f"检出病灶数 / Detected lesions: {num_lesions}",
                f"总体最高风险等级 / Highest risk level: {max_risk}",
            ]
            for line in meta_lines:
                story.append(Paragraph(line, styles["Body"]))
            story.append(Spacer(1, 12))

            story.append(
                Paragraph(
                    "1. 自动临床评估摘要 / Automated Clinical Assessment Summary",
                    styles["Heading"],
                )
            )

            summary_cn = f"综合分析显示患者总体风险为 {max_risk}。"
            if surgical_plans:
                summary_cn += f" 共识别出 {len(surgical_plans)} 个手术候选病灶。"
            else:
                summary_cn += " 当前未识别到需立即手术的病灶，建议定期随访。"

            summary_en = f"The overall risk profile is {max_risk}. "
            if surgical_plans:
                summary_en += f"{len(surgical_plans)} lesion(s) are identified as surgical candidates."
            else:
                summary_en += "No immediate surgical targets have been identified; regular follow-up is advised."

            story.append(Paragraph(summary_cn, styles["Body"]))
            story.append(Spacer(1, 4))
            story.append(Paragraph(summary_en, styles["Body"]))

            story.append(Paragraph("2. 病灶列表 / Lesion List", styles["Heading"]))

            lesion_table_data = [
                [
                    "ID",
                    "位置 / Pos",
                    "直径(mm)",
                    "风险等级 / Risk",
                    "尺寸分级 / Size",
                ]
            ]

            for l in lesion_analyses:
                pos = l.get("pos")
                dia = l.get("diameter_mm", 0.0)
                risk = l.get("risk_level", "")
                size_cat = l.get("size_category", "")
                lid = l.get("id", "")
                lesion_table_data.append(
                    [
                        str(lid),
                        str(pos),
                        f"{dia:.1f}",
                        str(risk),
                        str(size_cat),
                    ]
                )

            lesion_table = Table(lesion_table_data, repeatRows=1)
            lesion_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), base_font),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            story.append(lesion_table)

            if surgical_plans:
                story.append(
                    Paragraph(
                        "3. 手术路径与手术方式 / Surgical Path & Procedure",
                        styles["Heading"],
                    )
                )

                for plan in surgical_plans:
                    lid = plan.get("id")
                    lesion = next(
                        (l for l in lesion_analyses if l.get("id") == lid), None
                    )
                    desc_dict = plan.get("description") or {}
                    desc_cn = desc_dict.get("zh") or ""
                    desc_en = desc_dict.get("en") or ""
                    metrics = plan.get("metrics", {}) or {}
                    depth = metrics.get("depth_mm", 0.0)
                    angle_ax = metrics.get("angle_axial", 0.0)
                    angle_vt = metrics.get("angle_vertical", 0.0)

                    story.append(
                        Paragraph(
                            f"目标病灶 #{lid} / Target Lesion #{lid}",
                            styles["Body"],
                        )
                    )
                    if desc_cn:
                        story.append(
                            Paragraph(f"路径描述(中): {desc_cn}", styles["Body"])
                        )
                    if desc_en:
                        story.append(
                            Paragraph(
                                f"Path description (EN): {desc_en}", styles["Body"]
                            )
                        )

                    metric_cn = f"轨迹深度: {depth:.1f} mm；轴向角度: {angle_ax:.1f}°；垂直角度: {angle_vt:.1f}°"
                    metric_en = (
                        f"Trajectory depth: {depth:.1f} mm; axial angle: {angle_ax:.1f}°; "
                        f"vertical angle: {angle_vt:.1f}°"
                    )
                    story.append(Paragraph(metric_cn, styles["Body"]))
                    story.append(Paragraph(metric_en, styles["Body"]))

                    proc_cn = ""
                    proc_en = ""
                    if lesion:
                        tp_list = lesion.get("treatment_plan") or []
                        if tp_list:
                            top_tp = tp_list[0]
                            proc_cn = top_tp.get("name_zh") or ""
                            proc_en = top_tp.get("name_en") or ""
                        else:
                            sp = lesion.get("surgical_path") or {}
                            approaches = sp.get("approach") or []
                            if approaches:
                                top = approaches[0]
                                proc_cn = top.get("name_zh") or ""
                                proc_en = top.get("name_en") or ""

                    if proc_cn or proc_en:
                        text = "推荐手术方式: "
                        if proc_cn:
                            text += proc_cn
                        if proc_en:
                            text += f" / {proc_en}"
                        story.append(Paragraph(text, styles["Body"]))

                    story.append(Spacer(1, 6))

            tnm_rows = []
            for l in lesion_analyses:
                stage_info = l.get("stage_info") or {}
                if stage_info:
                    t_stage = stage_info.get("t_stage", "Tx")
                    c_stage = stage_info.get("clinical_stage_group", "Unknown")
                    lung_rads = l.get("lung_rads_score", "")
                    tnm_rows.append(
                        [
                            str(l.get("id", "")),
                            str(lung_rads),
                            str(t_stage),
                            str(c_stage),
                            str(l.get("risk_level", "")),
                        ]
                    )

            if tnm_rows:
                story.append(
                    Paragraph(
                        "4. TNM 分期表 / TNM Staging Table",
                        styles["Heading"],
                    )
                )
                tnm_table_data = [
                    [
                        "ID",
                        "Lung-RADS",
                        "T",
                        "临床分期 / Clinical Stage",
                        "风险等级 / Risk",
                    ]
                ] + tnm_rows
                tnm_table = Table(tnm_table_data, repeatRows=1)
                tnm_table.setStyle(
                    TableStyle(
                        [
                            ("FONTNAME", (0, 0), (-1, -1), base_font),
                            ("FONTSIZE", (0, 0), (-1, -1), 8),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ]
                    )
                )
                story.append(tnm_table)

            follow_rows = []
            for l in lesion_analyses:
                rec = l.get("recommendation")
                if rec:
                    rec_text = str(rec)
                    rec_para = Paragraph(rec_text, styles["Body"])
                    follow_rows.append(
                        [
                            str(l.get("id", "")),
                            str(l.get("risk_level", "")),
                            rec_para,
                        ]
                    )

            if follow_rows:
                story.append(
                    Paragraph(
                        "5. 随访建议表 / Follow-up Recommendations",
                        styles["Heading"],
                    )
                )

                from reportlab.pdfbase.pdfmetrics import stringWidth

                page_width, _ = A4
                available_width = page_width - doc.leftMargin - doc.rightMargin

                id_texts = [row[0] for row in follow_rows] or ["ID"]
                risk_texts = [row[1] for row in follow_rows] or ["风险等级"]

                def estimate_col_width(texts, min_w, max_w):
                    max_str = max(texts, key=lambda t: len(str(t)))
                    w = stringWidth(str(max_str), base_font, 8) + 10
                    return max(min_w, min(max_w, w))

                id_col_width = estimate_col_width(id_texts, 30, 60)
                risk_col_width = estimate_col_width(risk_texts, 60, 110)

                follow_col_width = max(
                    120, available_width - id_col_width - risk_col_width
                )

                follow_table_data = [
                    ["ID", "风险等级 / Risk", "随访与管理建议 / Follow-up Plan"]
                ] + follow_rows
                follow_table = Table(
                    follow_table_data,
                    repeatRows=1,
                    colWidths=[id_col_width, risk_col_width, follow_col_width],
                )
                follow_table.setStyle(
                    TableStyle(
                        [
                            ("FONTNAME", (0, 0), (-1, -1), base_font),
                            ("FONTSIZE", (0, 0), (-1, -1), 8),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ]
                    )
                )
                story.append(follow_table)

            if images:
                story.append(
                    Paragraph(
                        "6. 诊断影像预览 / Diagnostic Imaging Preview",
                        styles["Heading"],
                    )
                )
                story.append(
                    Paragraph(
                        "展示检出病灶的关键切片，红色轮廓表示 AI 分割边界。",
                        styles["Body"],
                    )
                )
                story.append(
                    Paragraph(
                        "Selected key slices demonstrating the detected lesions. "
                        "Red contours indicate the AI-segmented boundaries.",
                        styles["Body"],
                    )
                )

                for idx, im in enumerate(images[:3], 1):
                    try:
                        path_obj = Path(im)
                        if path_obj.exists():
                            stem = path_obj.stem
                            slice_label = None
                            for part in stem.split("_"):
                                if part.isdigit():
                                    try:
                                        slice_label = str(int(part))
                                    except ValueError:
                                        slice_label = part
                                    break

                            label_text = (
                                f"切片 {slice_label} / Slice {slice_label}"
                                if slice_label is not None
                                else f"切片 {idx} / Slice {idx}"
                            )
                            story.append(Spacer(1, 6))
                            story.append(
                                Paragraph(
                                    label_text,
                                    styles["Body"],
                                )
                            )
                            img_flow = Image(str(path_obj), width=160, height=160)
                            story.append(img_flow)
                    except Exception:
                        continue

            story.append(
                Paragraph(
                    "7. 免责声明与说明 / Disclaimer",
                    styles["Heading"],
                )
            )

            disclaimer_cn = (
                "本报告由 AI 辅助的医学影像分析系统生成，仅供研究与临床参考，"
                "不构成最终诊断或手术指令。所有临床决策须由具备资质的医疗专业人员综合判断。"
            )
            disclaimer_en = (
                "This report is generated by an AI-assisted medical imaging analysis system "
                "and is intended for research and clinical reference only. It does not constitute "
                "a definitive diagnosis or surgical instruction. All clinical decisions must be "
                "made by qualified medical professionals."
            )

            story.append(Paragraph(disclaimer_cn, styles["Body"]))
            story.append(Spacer(1, 4))
            story.append(Paragraph(disclaimer_en, styles["Body"]))

            doc.build(story)
            print(f"PDF 报告已生成: {pdf_path}", file=sys.stderr)

        except ImportError:
            print(
                "ReportLab 未安装，跳过 PDF 报告生成。请安装 reportlab 以启用 PDF 输出。",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"PDF 报告生成失败: {e}", file=sys.stderr)

        return html_path
