"""
Step 2 — enumerate every candidate image for every class and validate it.

    backend/.venv/Scripts/python scripts/vision/validate_images.py   → metadata/candidates.csv

An image is valid when PIL can fully decode it, it is RGB-convertible and at least 64×64 px.
quality_score (0–1) combines sharpness (Laplacian variance) and exposure; it is recorded, not used to drop.
"""
import hashlib
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from common import CLASSES, IMAGE_SUFFIXES, METADATA, OOD_TEST, ROOT, dhash_bits, extracted_dir, write_csv

MIN_SIDE = 64


def files_for(source: str, pattern: str):
    base = extracted_dir(source)
    for folder in sorted(base.glob(pattern)):
        if folder.is_dir():
            for file in sorted(folder.rglob("*")):
                if file.suffix.lower() in IMAGE_SUFFIXES and file.is_file():
                    yield file


def quality(image: Image.Image) -> float:
    gray = np.asarray(image.convert("L").resize((256, 256)), dtype=np.float32)
    lap = gray[1:-1, 1:-1] * 4 - gray[:-2, 1:-1] - gray[2:, 1:-1] - gray[1:-1, :-2] - gray[1:-1, 2:]
    sharp = min(1.0, float(lap.var()) / 300.0)
    exposure = 1.0 - min(1.0, abs(float(gray.mean()) - 128.0) / 128.0)
    return round(0.6 * sharp + 0.4 * exposure, 3)


def check(file: Path) -> dict:
    data = file.read_bytes()
    row = {"sha1": hashlib.sha1(data).hexdigest(), "valid": False, "reason": "", "width": 0, "height": 0, "quality_score": 0.0, "dhash": ""}
    try:
        with Image.open(file) as probe:
            probe.verify()
        with Image.open(file) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.load()
            row.update(width=img.width, height=img.height)
            if min(img.size) < MIN_SIDE:
                row["reason"] = "too_small"
                return row
            row.update(valid=True, quality_score=quality(img), dhash=f"{dhash_bits(img):016x}")
    except Exception as error:  # truncated/corrupt/unsupported file
        row["reason"] = f"corrupt:{type(error).__name__}"
    return row


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    rows = []
    jobs = [(label, src, pat) for label, (_, _, sources) in CLASSES.items() for src, pat in sources]
    jobs += [("ood_test", src, pat) for src, pat in OOD_TEST]
    for label, source, pattern in jobs:
        count = 0
        for file in files_for(source, pattern):
            rows.append({"label": label, "source_key": source, "raw_path": file.relative_to(ROOT).as_posix(),
                         "source_folder": file.parent.name, **check(file)})
            count += 1
        print(f"{label:28} {source:16} {pattern[-45:]:46} {count:5} files")
    write_csv(METADATA / "candidates.csv", rows)
    bad = [r for r in rows if not r["valid"]]
    print(f"{len(rows)} candidates, {len(bad)} invalid → metadata/candidates.csv")


if __name__ == "__main__":
    main()
