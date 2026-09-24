"""
Step 6 — cap over-represented classes (whole near-duplicate groups only).

    backend/.venv/Scripts/python scripts/vision/balance_classes.py   (updates metadata/manifest.csv)

Classes larger than MAX_PER_CLASS are down-sampled. Selection prefers field photos over lab photos and
spreads across sources, so a class isn't dominated by PlantVillage. Dropped rows get split = "not_selected".
Small classes are NOT up-sampled here — the training sampler weights them instead.
"""
import random
import sys
from collections import defaultdict

from common import MAX_OOD_TEST, MAX_PER_CLASS, MAX_UNSUPPORTED, METADATA, read_csv, write_csv

SEED = 42
STYLE_PRIORITY = {"field": 0, "field_web": 0, "lab": 1}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    rows = read_csv(METADATA / "manifest.csv")
    rng = random.Random(SEED)
    by_label = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_label[r["label"]][r["group_id"]].append(r)
    for label, groups in by_label.items():
        cap = MAX_UNSUPPORTED if label == "unsupported" else MAX_OOD_TEST if label == "ood_test" else MAX_PER_CLASS
        group_list = list(groups.values())
        rng.shuffle(group_list)
        # Field photos first, then round-robin across source datasets.
        by_source = defaultdict(list)
        for g in sorted(group_list, key=lambda g: STYLE_PRIORITY.get(g[0]["image_style"], 2)):
            by_source[g[0]["source_dataset"]].append(g)
        order = []
        while any(by_source.values()):
            for source in sorted(by_source, key=lambda s: STYLE_PRIORITY.get(by_source[s][0][0]["image_style"], 2) if by_source[s] else 9):
                if by_source[source]:
                    order.append(by_source[source].pop(0))
        taken = 0
        for group in order:
            keep = taken < cap
            for r in group:
                r["split"] = "" if keep else "not_selected"
            taken += len(group) if keep else 0
        print(f"{label:28} kept {min(taken, sum(len(g) for g in group_list)):5} of {sum(len(g) for g in group_list):5}")
    write_csv(METADATA / "manifest.csv", rows)


if __name__ == "__main__":
    main()
