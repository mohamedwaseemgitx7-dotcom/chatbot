"""
Field test: run the DEPLOYED model (backend/models/vision, ONNX) on your own farm photos.

    backend/.venv/Scripts/python ai/evaluation/field_test.py [folder]

Put photos in datasets/vision/field_test/<label>/*.jpg (label = a class name from classes.json, or
"unsupported" for other plants). This is the most honest accuracy check — do it with real photos from
Tamil Nadu fields before trusting the model. Output: per-class correct / wrong / uncertain counts.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.config.settings import get_settings  # noqa: E402
from app.vision.classifier import classify  # noqa: E402
from app.vision.preprocess import decode, to_tensor  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "datasets" / "vision" / "field_test"
    photos = [p for p in folder.glob("*/*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
    if not photos:
        raise SystemExit(f"No photos in {folder}/<label>/ — add real field photos first.")
    threshold = get_settings().IMAGE_CONFIDENCE_THRESHOLD
    results = defaultdict(Counter)
    for photo in photos:
        label = photo.parent.name
        (best, p), *_ = classify(to_tensor(decode(photo.read_bytes())))
        if best["name"] == "unsupported" or p < threshold:
            outcome = "correct" if label == "unsupported" else "uncertain"
        else:
            outcome = "correct" if best["name"] == label else "wrong"
        results[label][outcome] += 1
    total = Counter()
    for label, counts in sorted(results.items()):
        total.update(counts)
        print(f"{label:28} {dict(counts)}")
    n = sum(total.values())
    print(f"\nTOTAL {n} photos: correct {total['correct'] / n:.0%}, wrong {total['wrong'] / n:.0%}, uncertain {total['uncertain'] / n:.0%}")


if __name__ == "__main__":
    main()
