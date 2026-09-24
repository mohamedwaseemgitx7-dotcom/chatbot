"""
Runs the whole vision dataset pipeline in order (each step can also be run on its own):

    backend/.venv/Scripts/python scripts/vision/build_dataset.py

download_datasets → validate_images → remove_corrupt_images → detect_duplicates → generate_manifest
→ balance_classes → create_splits → dataset_report
"""
import runpy
import sys
from pathlib import Path

STEPS = ["download_datasets", "validate_images", "remove_corrupt_images", "detect_duplicates",
         "generate_manifest", "balance_classes", "create_splits", "dataset_report"]

if __name__ == "__main__":
    here = Path(__file__).parent
    sys.path.insert(0, str(here))
    for step in STEPS:
        print(f"\n===== {step} =====", flush=True)
        runpy.run_path(str(here / f"{step}.py"), run_name="__main__")
