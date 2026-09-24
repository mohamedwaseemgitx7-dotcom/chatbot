"""
Step 5 — write processed images and the manifest.

    backend/.venv/Scripts/python scripts/vision/generate_manifest.py   → processed/<label>/*.jpg, metadata/manifest.csv, metadata/classes.csv

Drops exact duplicates (one copy kept) and label-conflict groups. Images are resized to ≤ 384 px and
re-encoded as JPEG (training uses 224 px). Every manifest row carries source + licence information.
"""
import sys

from PIL import Image, ImageOps

from common import CLASSES, METADATA, PROCESSED, ROOT, SOURCES, read_csv, write_csv

MAX_SIDE = 384
FIELDS = ["image_id", "file_path", "crop", "condition", "label", "source_dataset", "source_url", "license", "license_url",
          "image_style", "group_id", "split", "verified", "quality_score", "original_file"]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    rows = [r for r in read_csv(METADATA / "duplicates.csv") if r["exact_duplicate"] == "False" and r["label_conflict"] == "False"]
    manifest = []
    for r in rows:
        label = r["label"]
        out = PROCESSED / label / f"{r['sha1'][:16]}.jpg"
        if not out.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(ROOT / r["raw_path"]) as img:
                img = ImageOps.exif_transpose(img).convert("RGB")
                img.thumbnail((MAX_SIDE, MAX_SIDE))
                img.save(out, "JPEG", quality=92)
        crop, condition = (CLASSES[label][0], CLASSES[label][1]) if label in CLASSES else (None, "Out-of-distribution test")
        source = SOURCES[r["source_key"]]
        manifest.append({
            "image_id": r["sha1"][:16], "file_path": out.relative_to(ROOT).as_posix(), "crop": crop or "none",
            "condition": condition, "label": label, "source_dataset": r["source_key"], "source_url": source["source_url"],
            "license": source["license"], "license_url": source["license_url"], "image_style": source["image_style"],
            "group_id": r["group_id"], "split": "", "verified": "author_labelled", "quality_score": r["quality_score"],
            "original_file": f"{r['source_folder']}/{r['raw_path'].rsplit('/', 1)[-1]}",
        })
    write_csv(METADATA / "manifest.csv", manifest, FIELDS)
    classes = [{"class_id": i, "label": label, "crop": crop or "none", "condition": cond,
                "sources": ";".join(sorted({s for s, _ in srcs}))} for i, (label, (crop, cond, srcs)) in enumerate(CLASSES.items())]
    write_csv(METADATA / "classes.csv", classes)
    print(f"{len(manifest)} images in manifest; {len(classes)} classes → metadata/classes.csv")


if __name__ == "__main__":
    main()
