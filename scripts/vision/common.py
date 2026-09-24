"""
Shared registry for the vision dataset pipeline: sources (with licences), classes, paths, hashing.

Every external dataset MUST be listed in SOURCES with its licence. download_datasets.py refuses any
source whose licence is not in ALLOWED_LICENSES, so nothing unlicensed can reach training.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VISION = ROOT / "datasets" / "vision"
RAW = VISION / "raw"                 # downloaded archives + extracted files (git-ignored)
PROCESSED = VISION / "processed"     # validated, resized JPEGs, one folder per label (git-ignored)
SPLITS = {s: VISION / s for s in ("train", "validation", "test")}  # hard links into processed/ (git-ignored)
METADATA = VISION / "metadata"       # manifest, classes, sources, licences, reports (committed)

DATASET_VERSION = "vision-2026.09.2"
ALLOWED_LICENSES = {"CC BY 4.0", "CC0 1.0"}
USER_AGENT = "FarmerAssist-dataset-downloader/1.0 (research; licensed datasets only)"

# ---------------------------------------------------------------------------------------------
# Sources. `files`: (archive name, download URL, expected sha256 or None when the host gives none).
# ---------------------------------------------------------------------------------------------
SOURCES = {
    "plantvillage": {
        "dataset_name": "PlantVillage (Data for: Identification of Plant Leaf Diseases Using a 9-layer Deep CNN)",
        "source_url": "https://data.mendeley.com/datasets/tywbtsjrjv/1",
        "license": "CC0 1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "citation": "Geetharamani G., Arun Pandian J. (2019). Mendeley Data, v1. doi:10.17632/tywbtsjrjv.1 "
                    "(images from Hughes & Salathé, PlantVillage, arXiv:1511.08060)",
        "usage_restrictions": "None (public domain dedication). Lab images on plain backgrounds — not representative of field photos.",
        "image_style": "lab",
        "files": [("Plant_leaf_diseases_dataset_without_augmentation.zip",
                   "https://data.mendeley.com/public-files/datasets/tywbtsjrjv/files/d5652a28-c1d8-4b76-97f3-72fb80f94efc/file_downloaded", "mendeley")],
    },
    "plantdoc": {
        "dataset_name": "PlantDoc (cropped classification set)",
        "source_url": "https://github.com/pratikkayal/PlantDoc-Dataset",
        "license": "CC BY 4.0",
        "license_url": "https://github.com/pratikkayal/PlantDoc-Dataset/blob/master/LICENSE.txt",
        "citation": "Singh D., Jain N., Jain P., Kayal P., Kumawat S., Batra N. (2020). PlantDoc: A Dataset for Visual "
                    "Plant Disease Detection. CoDS-COMAD 2020, pp. 249-253. doi:10.1145/3371158.3371196",
        "usage_restrictions": "Attribution required. Images were collected from the internet by the authors and manually "
                              "annotated; copyright of individual photos may remain with their original owners — "
                              "use for research/non-commercial purposes and keep attribution.",
        "image_style": "field_web",
        "files": [("PlantDoc-Dataset-master.zip", "https://codeload.github.com/pratikkayal/PlantDoc-Dataset/zip/refs/heads/master", None)],
    },
    "riceleafbd": {
        "dataset_name": "RiceLeafBD: A Real-Field Image Dataset for Rice Leaf Disease Detection and Classification in Bangladesh",
        "source_url": "https://data.mendeley.com/datasets/kx9rx8p2mz/1",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "citation": "RiceLeafBD, Mendeley Data v1, doi:10.17632/kx9rx8p2mz.1",
        "usage_restrictions": "Attribution required.",
        "image_style": "field",
        "files": [("Original Images.zip", "https://data.mendeley.com/public-files/datasets/kx9rx8p2mz/files/fdab2bd9-ed8b-4156-8d96-0b5d8f18f4ed/file_downloaded", "mendeley")],
    },
    "rice_samples": {
        "dataset_name": "Rice Leaf Disease Image Samples",
        "source_url": "https://data.mendeley.com/datasets/fwcj7stb8r/1",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "citation": "Sethy P. K. (2020). Rice Leaf Disease Image Samples, Mendeley Data v1, doi:10.17632/fwcj7stb8r.1",
        "usage_restrictions": "Attribution required.",
        "image_style": "field",
        "files": [("Rice Leaf Disease Images.7z", "MENDELEY:fwcj7stb8r", "mendeley")],
    },
    "chilli_mendeley": {
        "dataset_name": "Chilli Leaf Disease Image Dataset for Classification and Early Diagnosis in Agriculture",
        "source_url": "https://data.mendeley.com/datasets/tm3v4zmh7c/1",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "citation": "Chilli Leaf Disease Image Dataset, Mendeley Data v1, doi:10.17632/tm3v4zmh7c.1",
        "usage_restrictions": "Attribution required.",
        "image_style": "field",
        "files": [("Curl_Virus.zip", "https://data.mendeley.com/public-files/datasets/tm3v4zmh7c/files/d94a4729-47ec-4a39-bead-498e16347c4d/file_downloaded", "mendeley"),
                  ("Healthy_Leaf.zip", "https://data.mendeley.com/public-files/datasets/tm3v4zmh7c/files/5754b152-c21f-4989-b5fe-a370c32b9409/file_downloaded", "mendeley")],
    },
    "banana_mendeley": {
        "dataset_name": "Banana Leaf Disease Images",
        "source_url": "https://data.mendeley.com/datasets/rjykr62kdh/1",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "citation": "Banana Leaf Disease Images, Mendeley Data v1, doi:10.17632/rjykr62kdh.1",
        "usage_restrictions": "Attribution required.",
        "image_style": "field",
        "files": [("Banana Leaf Images.rar", "https://data.mendeley.com/public-files/datasets/rjykr62kdh/files/bb17acd2-53db-4e7c-b5d0-cc2e41846237/file_downloaded", "mendeley")],
    },
}

# ---------------------------------------------------------------------------------------------
# Classes: label → crop, condition, and the source folders (glob-style relative to raw/<source>/extracted).
# Only classes with enough licensed images are listed; nothing is invented.
# ---------------------------------------------------------------------------------------------
PV = "Plant_leave_diseases_dataset_without_augmentation"
PD_TRAIN, PD_TEST = "PlantDoc-Dataset-master/train", "PlantDoc-Dataset-master/test"

CLASSES = {
    "rice_healthy": ("paddy", "Healthy", [("riceleafbd", "Original Images/Healthy Leaf")]),
    "rice_brown_spot": ("paddy", "Brown spot", [("riceleafbd", "Original Images/Brown Spot"), ("rice_samples", "*/Brownspot")]),
    "rice_bacterial_leaf_blight": ("paddy", "Bacterial leaf blight", [("riceleafbd", "Original Images/Bacterial Leaf Blight"), ("rice_samples", "*/Bacterialblight")]),
    "rice_leaf_blast": ("paddy", "Leaf blast", [("rice_samples", "*/Blast")]),
    "tomato_healthy": ("tomato", "Healthy", [("plantvillage", f"{PV}/Tomato___healthy"), ("plantdoc", f"{PD_TRAIN}/Tomato leaf"), ("plantdoc", f"{PD_TEST}/Tomato leaf")]),
    "tomato_early_blight": ("tomato", "Early blight", [("plantvillage", f"{PV}/Tomato___Early_blight"), ("plantdoc", f"{PD_TRAIN}/Tomato Early blight leaf"), ("plantdoc", f"{PD_TEST}/Tomato Early blight leaf")]),
    "tomato_late_blight": ("tomato", "Late blight", [("plantvillage", f"{PV}/Tomato___Late_blight"), ("plantdoc", f"{PD_TRAIN}/Tomato leaf late blight"), ("plantdoc", f"{PD_TEST}/Tomato leaf late blight")]),
    "tomato_leaf_mold": ("tomato", "Leaf mold", [("plantvillage", f"{PV}/Tomato___Leaf_Mold"), ("plantdoc", f"{PD_TRAIN}/Tomato mold leaf"), ("plantdoc", f"{PD_TEST}/Tomato mold leaf")]),
    "tomato_septoria_leaf_spot": ("tomato", "Septoria leaf spot", [("plantvillage", f"{PV}/Tomato___Septoria_leaf_spot"), ("plantdoc", f"{PD_TRAIN}/Tomato Septoria leaf spot"), ("plantdoc", f"{PD_TEST}/Tomato Septoria leaf spot")]),
    "chilli_healthy": ("chilli", "Healthy", [("chilli_mendeley", "Healthy_Leaf")]),
    "chilli_leaf_curl": ("chilli", "Leaf curl", [("chilli_mendeley", "Curl_Virus")]),
    "banana_healthy": ("banana", "Healthy", [("banana_mendeley", "resized/healthy")]),
    "banana_leaf_disease": ("banana", "Sigatoka leaf spot", [("banana_mendeley", "resized/segatoka")]),
    "maize_healthy": ("maize", "Healthy", [("plantvillage", f"{PV}/Corn___healthy")]),
    "maize_common_rust": ("maize", "Common rust", [("plantvillage", f"{PV}/Corn___Common_rust"), ("plantdoc", f"{PD_TRAIN}/Corn rust leaf"), ("plantdoc", f"{PD_TEST}/Corn rust leaf")]),
    "maize_northern_leaf_blight": ("maize", "Northern leaf blight", [("plantvillage", f"{PV}/Corn___Northern_Leaf_Blight"), ("plantdoc", f"{PD_TRAIN}/Corn leaf blight"), ("plantdoc", f"{PD_TEST}/Corn leaf blight")]),
    "maize_gray_leaf_spot": ("maize", "Gray leaf spot", [("plantvillage", f"{PV}/Corn___Cercospora_leaf_spot Gray_leaf_spot"), ("plantdoc", f"{PD_TRAIN}/Corn Gray leaf spot"), ("plantdoc", f"{PD_TEST}/Corn Gray leaf spot")]),
    # Photos the model must NOT force into a supported class: other crops and uncovered diseases.
    "unsupported": (None, "Unsupported", [
        ("plantvillage", f"{PV}/Apple___*"), ("plantvillage", f"{PV}/Grape___*"), ("plantvillage", f"{PV}/Peach___*"),
        ("plantvillage", f"{PV}/Cherry___*"), ("plantvillage", f"{PV}/Squash___*"), ("plantvillage", f"{PV}/Orange___*"),
        ("plantvillage", f"{PV}/Blueberry___*"),
        # Tomato problems FarmerAssist does not classify (must not be forced into a supported class)
        ("plantvillage", f"{PV}/Tomato___Bacterial_spot"), ("plantvillage", f"{PV}/Tomato___Tomato_mosaic_virus"),
        ("plantvillage", f"{PV}/Tomato___Tomato_Yellow_Leaf_Curl_Virus"), ("plantvillage", f"{PV}/Tomato___Spider_mites Two-spotted_spider_mite"),
        ("plantvillage", f"{PV}/Tomato___Target_Spot"),
        ("plantdoc", f"{PD_TRAIN}/Tomato leaf bacterial spot"), ("plantdoc", f"{PD_TRAIN}/Tomato leaf mosaic virus"),
        ("plantdoc", f"{PD_TRAIN}/Tomato leaf yellow virus"), ("plantdoc", f"{PD_TRAIN}/Tomato two spotted spider mites leaf"),
        ("plantdoc", f"{PD_TRAIN}/Apple*"), ("plantdoc", f"{PD_TRAIN}/grape*"), ("plantdoc", f"{PD_TRAIN}/Cherry*"),
        ("plantdoc", f"{PD_TRAIN}/Peach*"), ("plantdoc", f"{PD_TRAIN}/Squash*"), ("plantdoc", f"{PD_TRAIN}/Blueberry*"),
        ("riceleafbd", "Original Images/Tungro Virus"), ("rice_samples", "*/Tungro"), ("banana_mendeley", "resized/xamthomonas"),
    ]),
}
# Never used for training: measures rejection of plants the model has never seen (lab + field photos).
OOD_TEST = [
    ("plantvillage", f"{PV}/Potato___*"), ("plantvillage", f"{PV}/Pepper,_bell___*"), ("plantvillage", f"{PV}/Strawberry___*"),
    ("plantvillage", f"{PV}/Soybean___*"), ("plantvillage", f"{PV}/Raspberry___*"),
    ("plantdoc", f"{PD_TEST}/Potato*"), ("plantdoc", f"{PD_TEST}/Bell_pepper*"), ("plantdoc", f"{PD_TEST}/Strawberry*"),
    ("plantdoc", f"{PD_TEST}/Soyabean*"), ("plantdoc", f"{PD_TEST}/Raspberry*"), ("plantdoc", f"{PD_TRAIN}/Potato*"),
    ("plantdoc", f"{PD_TRAIN}/Bell_pepper*"),
]
MAX_PER_CLASS = 1500
MAX_UNSUPPORTED = 2000
MAX_OOD_TEST = 600
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def extracted_dir(source: str) -> Path:
    return RAW / source / "extracted"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def dhash_bits(image) -> int:
    """64-bit difference hash of a PIL image (robust to resizing/re-encoding)."""
    import numpy as np
    from PIL import Image

    small = np.asarray(image.convert("L").resize((9, 8), Image.BILINEAR), dtype=np.int16)
    value = 0
    for bit in (small[:, 1:] > small[:, :-1]).flatten():
        value = (value << 1) | int(bit)
    return value


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or (list(rows[0]) if rows else [])
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
