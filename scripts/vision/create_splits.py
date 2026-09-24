"""
Step 7 — group-aware, stratified train/validation/test split + split folders.

    backend/.venv/Scripts/python scripts/vision/create_splits.py

- a near-duplicate group always lands in ONE split (no leakage of copies/augmentations)
- PlantDoc's own test folder stays in test (it is the external field-style benchmark)
- 70/15/15 per class and per source dataset, so every source is represented in every split
- ood_test images keep split "ood_test" (never trained on)
- datasets/vision/{train,validation,test}/<label>/ are filled with hard links into processed/ (no extra disk)
"""
import os
import random
import shutil
import sys
from collections import defaultdict

from common import METADATA, ROOT, SPLITS, read_csv, write_csv

SEED = 42


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    rows = read_csv(METADATA / "manifest.csv")
    rng = random.Random(SEED)
    # Images from PlantDoc's own test folder (from the raw path recorded at validation time).
    plantdoc_test = {c["sha1"][:16] for c in read_csv(METADATA / "candidates.csv")
                     if c["source_key"] == "plantdoc" and "/test/" in c["raw_path"]}

    groups_by_bucket = defaultdict(lambda: defaultdict(list))  # (label, source) → group → rows
    for r in rows:
        if r["split"] == "not_selected":
            continue
        if r["label"] == "ood_test":
            r["split"] = "ood_test"
            continue
        groups_by_bucket[(r["label"], r["source_dataset"])][r["group_id"]].append(r)

    buckets = defaultdict(dict)
    for key, groups in groups_by_bucket.items():
        for gid, members in groups.items():
            if any(m["image_id"] in plantdoc_test for m in members):
                for m in members:  # the whole group follows PlantDoc's test assignment
                    m["split"] = "test"
            else:
                buckets[key][gid] = members

    for (label, source), groups in buckets.items():
        group_list = list(groups.values())
        rng.shuffle(group_list)
        total = sum(len(g) for g in group_list)
        taken = 0
        for group in group_list:
            fraction = taken / max(total, 1)
            split = "train" if fraction < 0.70 else "validation" if fraction < 0.85 else "test"
            for r in group:
                r["split"] = split
            taken += len(group)

    write_csv(METADATA / "manifest.csv", rows)
    for folder in SPLITS.values():
        if folder.exists():
            shutil.rmtree(folder)
    for r in rows:
        if r["split"] in SPLITS:
            target = SPLITS[r["split"]] / r["label"] / f"{r['image_id']}.jpg"
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(ROOT / r["file_path"], target)
            except OSError:
                shutil.copyfile(ROOT / r["file_path"], target)
    counts = defaultdict(int)
    for r in rows:
        counts[r["split"]] += 1
    print(dict(counts))


if __name__ == "__main__":
    main()
