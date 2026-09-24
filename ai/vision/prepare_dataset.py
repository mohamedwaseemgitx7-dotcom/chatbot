"""
Builds the training image set from the downloaded archives (offline step).

    backend/.venv/Scripts/python ai/vision/prepare_dataset.py

- extracts only the 10 FarmerAssist classes (datasets/vision/image_classes.csv)
- downsizes to ≤ 320 px (training uses 224) and re-encodes as JPEG → data/vision/images/<class>/
- groups near-identical photos by perceptual hash so duplicates never straddle train/validation/test
- stratified 70/15/15 split (seeded) per class, groups kept together
- writes datasets/vision/image_dataset_manifest.csv with source + licence for every image
Labels are the dataset authors' labels ("verified" = author_labelled; not re-checked by an agronomist).
"""
import csv
import hashlib
import io
import random
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "vision_raw"
OUT = ROOT / "data" / "vision" / "images"
MANIFEST = ROOT / "datasets" / "vision" / "image_dataset_manifest.csv"
MAX_SIDE = 320
MAX_PER_CLASS = 1200
SEED = 42

# class → (archive, folder prefix inside archive, source key)
CLASSES = {
    "rice_healthy": ("rice_riceleafbd/Original Images.zip", "Original Images/Healthy Leaf/", "riceleafbd"),
    "rice_brown_spot": ("rice_riceleafbd/Original Images.zip", "Original Images/Brown Spot/", "riceleafbd"),
    "rice_leaf_blight": ("rice_riceleafbd/Original Images.zip", "Original Images/Bacterial Leaf Blight/", "riceleafbd"),
    "tomato_healthy": ("tomato_plantvillage/Plant_leaf_diseases_dataset_without_augmentation.zip", "Plant_leave_diseases_dataset_without_augmentation/Tomato___healthy/", "plantvillage"),
    "tomato_leaf_spot": ("tomato_plantvillage/Plant_leaf_diseases_dataset_without_augmentation.zip", "Plant_leave_diseases_dataset_without_augmentation/Tomato___Septoria_leaf_spot/", "plantvillage"),
    "tomato_early_blight": ("tomato_plantvillage/Plant_leaf_diseases_dataset_without_augmentation.zip", "Plant_leave_diseases_dataset_without_augmentation/Tomato___Early_blight/", "plantvillage"),
    "chilli_healthy": ("chilli_tm3v4zmh7c/Healthy_Leaf.zip", "Healthy_Leaf/", "chilli_mendeley"),
    "chilli_leaf_curl": ("chilli_tm3v4zmh7c/Curl_Virus.zip", "Curl_Virus/", "chilli_mendeley"),
    "banana_healthy": ("banana_rjykr62kdh/extracted", "resized/healthy/", "banana_mendeley"),
    "banana_leaf_disease": ("banana_rjykr62kdh/extracted", "resized/segatoka/", "banana_mendeley"),
}
PV = "tomato_plantvillage/Plant_leaf_diseases_dataset_without_augmentation.zip"
PV_PREFIX = "Plant_leave_diseases_dataset_without_augmentation/"
# "unsupported": photos the model must NOT force into a supported class — other crops, and diseases of
# supported crops that FarmerAssist doesn't cover (rice tungro, banana Xanthomonas wilt).
UNSUPPORTED_SOURCES = [
    (PV, [f"{PV_PREFIX}{c}/" for c in ("Apple___Apple_scab", "Apple___healthy", "Grape___Black_rot", "Grape___healthy",
                                        "Corn___Common_rust", "Corn___healthy", "Peach___Bacterial_spot", "Cherry___healthy",
                                        "Squash___Powdery_mildew", "Orange___Haunglongbing_(Citrus_greening)", "Blueberry___healthy")],
     "plantvillage", 700),
    ("rice_riceleafbd/Original Images.zip", ["Original Images/Tungro Virus/"], "riceleafbd", 250),
    ("banana_rjykr62kdh/extracted", ["resized/xamthomonas/"], "banana_mendeley", 250),
]
# Never trained on: measures whether rejection generalises to plants the model has never seen.
OOD_TEST_SOURCES = [(PV, [f"{PV_PREFIX}{c}/" for c in ("Potato___Early_blight", "Potato___healthy", "Pepper,_bell___Bacterial_spot",
                                                       "Pepper,_bell___healthy", "Strawberry___Leaf_scorch", "Soybean___healthy",
                                                       "Raspberry___healthy")], "plantvillage", 350)]

SOURCES = {
    "riceleafbd": ("RiceLeafBD (Mendeley Data kx9rx8p2mz v1)", "CC BY 4.0"),
    "plantvillage": ("PlantVillage via Mendeley Data tywbtsjrjv v1", "CC0 1.0"),
    "chilli_mendeley": ("Chilli Leaf Disease Image Dataset (Mendeley Data tm3v4zmh7c v1)", "CC BY 4.0"),
    "banana_mendeley": ("Banana Leaf Disease Images (Mendeley Data rjykr62kdh v1)", "CC BY 4.0"),
}
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def dhash(image: Image.Image) -> str:
    small = np.asarray(image.convert("L").resize((9, 8), Image.BILINEAR), dtype=np.int16)
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    return "%016x" % int("".join("1" if b else "0" for b in bits), 2)


def iter_images(archive: str, prefix: str):
    path = RAW / archive
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if name.startswith(prefix) and name.lower().endswith(IMAGE_SUFFIXES):
                    yield name, z.read(name)
    else:  # an extracted folder (the banana .rar is extracted with Windows tar first)
        for file in sorted((path / prefix).glob("*")):
            if file.suffix.lower() in IMAGE_SUFFIXES:
                yield file.name, file.read_bytes()


def ensure_banana_extracted():
    target = RAW / "banana_rjykr62kdh" / "extracted"
    if not target.exists():
        import subprocess

        target.mkdir(parents=True)
        # Windows 10+ bsdtar reads RAR archives.
        subprocess.run([r"C:\Windows\System32\tar.exe", "-xf", str(RAW / "banana_rjykr62kdh" / "Banana Leaf Images.rar"), "-C", str(target)], check=True)


def load_groups(sources):
    """[(archive, [prefixes], source_key, cap_per_prefix_total)] → perceptual-hash groups of (digest, name, image, source)."""
    groups: dict[str, list] = defaultdict(list)
    seen_bytes = set()
    for archive, prefixes, source, cap in sources:
        per_prefix = max(1, cap // len(prefixes))
        for prefix in prefixes:
            taken = 0
            for name, data in iter_images(archive, prefix):
                if taken >= per_prefix:
                    break
                digest = hashlib.sha1(data).hexdigest()
                if digest in seen_bytes:
                    continue
                seen_bytes.add(digest)
                try:
                    image = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
                except Exception:
                    continue
                image.thumbnail((MAX_SIDE, MAX_SIDE))
                groups[dhash(image)].append((digest, name, image, source))
                taken += 1
    return groups


def write_split(label, groups, rng, rows, fixed_split=None):
    (OUT / label).mkdir(parents=True, exist_ok=True)
    group_list = list(groups.values())
    rng.shuffle(group_list)
    total = min(MAX_PER_CLASS, sum(len(g) for g in group_list))
    taken, split_rows = 0, []
    for group in group_list:
        if taken >= total:
            break
        fraction = taken / total
        split = fixed_split or ("train" if fraction < 0.70 else "validation" if fraction < 0.85 else "test")
        for digest, name, image, source in group:
            file = OUT / label / f"{digest[:16]}.jpg"
            if not file.exists():
                image.save(file, "JPEG", quality=90)
            split_rows.append({
                "image_id": digest[:16], "image_path": str(file.relative_to(ROOT)).replace("\\", "/"),
                "crop": "none" if label == "unsupported" else label.split("_")[0].replace("rice", "paddy"),
                "label": label, "split": split,
                "source": f"{SOURCES[source][0]}: {name}", "license": SOURCES[source][1], "verified": "author_labelled",
            })
            taken += 1
    counts = {s: sum(r["split"] == s for r in split_rows) for s in ("train", "validation", "test", "ood_test")}
    print(f"{label:22} {len(split_rows):5} images ({len(groups)} hash groups) {counts}")
    rows.extend(split_rows)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ensure_banana_extracted()
    rng = random.Random(SEED)
    rows = []
    write_split("unsupported", load_groups(UNSUPPORTED_SOURCES), rng, rows)
    ood = load_groups(OOD_TEST_SOURCES)
    write_split("unsupported", ood, rng, rows, fixed_split="ood_test")
    for label, (archive, prefix, source) in CLASSES.items():
        (OUT / label).mkdir(parents=True, exist_ok=True)
        groups: dict[str, list] = defaultdict(list)
        seen_bytes = set()
        for name, data in iter_images(archive, prefix):
            digest = hashlib.sha1(data).hexdigest()
            if digest in seen_bytes:  # exact duplicate file
                continue
            seen_bytes.add(digest)
            try:
                image = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
            except Exception:
                continue  # unreadable file: skipped, not guessed
            image.thumbnail((MAX_SIDE, MAX_SIDE))
            groups[dhash(image)].append((digest, name, image))

        group_list = list(groups.values())
        rng.shuffle(group_list)
        total = min(MAX_PER_CLASS, sum(len(g) for g in group_list))
        taken, split_rows = 0, []
        for group in group_list:
            if taken >= total:
                break
            fraction = taken / total
            split = "train" if fraction < 0.70 else "validation" if fraction < 0.85 else "test"
            for digest, name, image in group:
                file = OUT / label / f"{digest[:16]}.jpg"
                if not file.exists():
                    image.save(file, "JPEG", quality=90)
                split_rows.append({
                    "image_id": digest[:16], "image_path": str(file.relative_to(ROOT)).replace("\\", "/"),
                    "crop": label.split("_")[0].replace("rice", "paddy"), "label": label, "split": split,
                    "source": f"{SOURCES[source][0]}: {name}", "license": SOURCES[source][1], "verified": "author_labelled",
                })
                taken += 1
        counts = {s: sum(r["split"] == s for r in split_rows) for s in ("train", "validation", "test")}
        print(f"{label:22} {len(split_rows):5} images ({len(groups)} hash groups) {counts}")
        rows.extend(split_rows)

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} images → {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
