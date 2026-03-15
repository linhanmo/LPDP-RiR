import os
import shutil
from pathlib import Path


def main():
    project_root = Path(__file__).resolve().parent
    output_base_dir = project_root / "application" / "output"
    report_dest_dir = project_root / "report"
    pdf_dest_dir = project_root / "pdf"

    if not report_dest_dir.exists():
        report_dest_dir.mkdir(parents=True)
        print(f"Created report directory: {report_dest_dir}")

    if not pdf_dest_dir.exists():
        pdf_dest_dir.mkdir(parents=True)
        print(f"Created pdf directory: {pdf_dest_dir}")

    if not output_base_dir.exists():
        print(f"Error: Output directory not found: {output_base_dir}")
        return

    subdirs = [d for d in output_base_dir.iterdir() if d.is_dir()]

    subdirs.sort(key=lambda x: x.name)

    print(f"Found {len(subdirs)} subdirectories in {output_base_dir}")

    count = 0
    for subdir in subdirs:
        case_id = subdir.name

        source_html = subdir / "report.html"

        if source_html.exists():
            print(f"[{case_id}] Found HTML report.")

            dest_html = report_dest_dir / f"{case_id}.html"

            try:
                shutil.copy2(source_html, dest_html)
                print(f"[{case_id}] Copied HTML to {dest_html.name}")
                count += 1
            except Exception as e:
                print(f"[{case_id}] Error copying HTML file: {e}")
        else:
            print(f"[{case_id}] HTML report not found in output folder. Skipping HTML.")

        pdf_source = None
        candidates = [
            subdir / "report.pdf",
            subdir / "medical_report.pdf",
        ]
        for c in candidates:
            if c.exists():
                pdf_source = c
                break

        if pdf_source is None:
            pdf_files = sorted(subdir.glob("*.pdf"))
            if len(pdf_files) == 1:
                pdf_source = pdf_files[0]

        if pdf_source is not None:
            dest_pdf = pdf_dest_dir / f"{case_id}.pdf"
            try:
                shutil.copy2(pdf_source, dest_pdf)
                print(f"[{case_id}] Copied PDF to {dest_pdf.name}")
            except Exception as e:
                print(f"[{case_id}] Error copying PDF file: {e}")
        else:
            print(f"[{case_id}] PDF report not found in output folder. Skipping PDF.")

    print(f"\nProcessing complete. {count} reports collected.")


if __name__ == "__main__":
    main()
