import os
import sys
import glob
import subprocess
import shutil
from pathlib import Path
import re


def natural_sort_key(s):
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split("([0-9]+)", str(s))
    ]


def main():
    project_root = Path(__file__).resolve().parent
    dataset_dir = project_root / "dataset"
    model_script = project_root / "application" / "model" / "model.py"
    output_base_dir = project_root / "application" / "output"
    input_base_dir = project_root / "application" / "input"
    files = glob.glob(str(dataset_dir / "*.npz"))
    if not files:
        print(f"No .npz files found in {dataset_dir}")
        return
    files.sort(key=natural_sort_key)
    print(f"Found {len(files)} samples.")
    for i, file_path in enumerate(files, start=1):
        target_name = f"{i:04d}"
        target_dir = output_base_dir / target_name
        target_input_dir = input_base_dir / target_name
        print(
            f"[{i}/{len(files)}] Processing {os.path.basename(file_path)} -> {target_name}"
        )
        if target_dir.exists():
            print(f"  Target output {target_name} already exists. Removing...")
            try:
                shutil.rmtree(target_dir)
            except Exception as e:
                print(f"  Error removing {target_dir}: {e}")
                continue
        if target_input_dir.exists():
            print(f"  Target input {target_name} already exists. Removing...")
            try:
                shutil.rmtree(target_input_dir)
            except Exception as e:
                print(f"  Error removing {target_input_dir}: {e}")
                continue
        cmd = [sys.executable, str(model_script), "--input", file_path]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            if result.returncode != 0:
                print(f"  Error running model.py: {result.stderr}")
                continue
            output_dir = None
            input_dir = None
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("OUTPUT_DIR:"):
                    output_dir = Path(line.split("OUTPUT_DIR:")[1].strip())
                elif line.startswith("INPUT_DIR:"):
                    input_dir = Path(line.split("INPUT_DIR:")[1].strip())
            if output_dir and output_dir.exists():
                try:
                    output_dir.rename(target_dir)
                    print(f"  Renamed output to {target_name}")
                except Exception as e:
                    print(f"  Failed to rename {output_dir} to {target_dir}: {e}")
            else:
                print(
                    f"  Could not find output directory in stdout or it doesn't exist."
                )
            if input_dir and input_dir.exists():
                try:
                    input_dir.rename(target_input_dir)
                    print(f"  Renamed input to {target_name}")
                except Exception as e:
                    print(f"  Failed to rename {input_dir} to {target_input_dir}: {e}")
        except Exception as e:
            print(f"  Exception during processing: {e}")
    print("Batch processing complete.")


if __name__ == "__main__":
    main()
