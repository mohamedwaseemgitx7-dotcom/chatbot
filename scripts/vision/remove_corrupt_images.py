"""
Step 3 — remove corrupt/too-small files found by validate_images.py.

    backend/.venv/Scripts/python scripts/vision/remove_corrupt_images.py

Deletes them from the extracted raw folders (the original archives are untouched, so this is reversible
by re-extracting) and logs every removal to metadata/removed_images.csv.
"""
import sys

from common import METADATA, ROOT, read_csv, write_csv


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    rows = read_csv(METADATA / "candidates.csv")
    removed = []
    for r in rows:
        if r["valid"] != "True":
            path = ROOT / r["raw_path"]
            if path.exists():
                path.unlink()
            removed.append({"raw_path": r["raw_path"], "label": r["label"], "reason": r["reason"]})
    kept = [r for r in rows if r["valid"] == "True"]
    write_csv(METADATA / "removed_images.csv", removed, ["raw_path", "label", "reason"])
    write_csv(METADATA / "candidates.csv", kept)
    print(f"removed {len(removed)} invalid images; {len(kept)} remain")


if __name__ == "__main__":
    main()
