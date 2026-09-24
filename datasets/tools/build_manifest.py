"""Build image_dataset_manifest.csv from real images you have downloaded.

Expected layout (class folder names must match vision/image_classes.csv):
    images/<class_name>/<file>.jpg
Also create images/SOURCES.csv with: class_name,source,license   (one row per class or per source)

Usage:  python build_manifest.py images ../vision/image_dataset_manifest.csv
Splits 70/15/15 per class. Near-duplicate photos (same leaf, burst shots) should share a prefix
like leafA_01.jpg, leafA_02.jpg — files with the same prefix before '_' stay in one split.
"""
import csv, hashlib, os, random, sys
from collections import defaultdict
random.seed(7)
root, out = sys.argv[1], sys.argv[2]
src = {}
if os.path.exists(os.path.join(root, "SOURCES.csv")):
    for r in csv.DictReader(open(os.path.join(root, "SOURCES.csv"), encoding="utf-8")):
        src[r["class_name"]] = (r["source"], r["license"])
rows, seen = [], set()
for cls in sorted(os.listdir(root)):
    d = os.path.join(root, cls)
    if not os.path.isdir(d): continue
    groups = defaultdict(list)
    for f in sorted(os.listdir(d)):
        if not f.lower().endswith((".jpg", ".jpeg", ".png")): continue
        h = hashlib.md5(open(os.path.join(d, f), "rb").read()).hexdigest()
        if h in seen: continue          # exact duplicate image
        seen.add(h); groups[f.split("_")[0]].append(f)
    keys = list(groups); random.shuffle(keys)
    n = len(keys); nt = max(1, round(n * .15)); nv = max(1, round(n * .15))
    for i, k in enumerate(keys):
        split = "test" if i < nt else "validation" if i < nt + nv else "train"
        for f in groups[k]:
            s, l = src.get(cls, ("UNKNOWN", "UNKNOWN"))
            rows.append(dict(image_id=f"IMG{len(rows)+1:06d}", image_path=f"{cls}/{f}", crop=cls.split("_")[0],
                             label=cls, split=split, source=s, license=l, verified="false"))
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["image_id", "image_path", "crop", "label", "split", "source", "license", "verified"])
    w.writeheader(); w.writerows(rows)
print(f"{len(rows)} images written to {out}")
