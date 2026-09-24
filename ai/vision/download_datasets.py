"""
Downloads the licensed crop-leaf image datasets used to train the vision model (offline step).

    backend/.venv/Scripts/python ai/vision/download_datasets.py

All sources are Mendeley Data; licences were checked via the Mendeley public API before use.
Archives go to data/vision_raw/ (git-ignored) and are verified against Mendeley's SHA-256 hashes.
"""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "vision_raw"
# Mendeley rejects the default "Python-urllib" agent; identify the client honestly instead.
USER_AGENT = "FarmerAssist-dataset-downloader/1.0 (research; CC-licensed datasets)"


def open_url(url: str, timeout: int = 60):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=timeout)

SOURCES = [
    {
        "key": "rice_riceleafbd",
        "dataset": "RiceLeafBD: A Real-Field Image Dataset for Rice Leaf Disease Detection and Classification in Bangladesh",
        "url": "https://data.mendeley.com/datasets/kx9rx8p2mz/1",
        "licence": "CC BY 4.0",
        "files": [("Original Images.zip", "https://data.mendeley.com/public-files/datasets/kx9rx8p2mz/files/fdab2bd9-ed8b-4156-8d96-0b5d8f18f4ed/file_downloaded")],
    },
    {
        "key": "chilli_tm3v4zmh7c",
        "dataset": "Chilli Leaf Disease Image Dataset for Classification and Early Diagnosis in Agriculture",
        "url": "https://data.mendeley.com/datasets/tm3v4zmh7c/1",
        "licence": "CC BY 4.0",
        "files": [
            ("Curl_Virus.zip", "https://data.mendeley.com/public-files/datasets/tm3v4zmh7c/files/d94a4729-47ec-4a39-bead-498e16347c4d/file_downloaded"),
            ("Healthy_Leaf.zip", "https://data.mendeley.com/public-files/datasets/tm3v4zmh7c/files/5754b152-c21f-4989-b5fe-a370c32b9409/file_downloaded"),
        ],
    },
    {
        "key": "banana_rjykr62kdh",
        "dataset": "Banana Leaf Disease Images",
        "url": "https://data.mendeley.com/datasets/rjykr62kdh/1",
        "licence": "CC BY 4.0",
        "files": [("Banana Leaf Images.rar", "https://data.mendeley.com/public-files/datasets/rjykr62kdh/files/bb17acd2-53db-4e7c-b5d0-cc2e41846237/file_downloaded")],
    },
    {
        "key": "tomato_plantvillage",
        "dataset": "PlantVillage (Data for: Identification of Plant Leaf Diseases Using a 9-layer Deep CNN)",
        "url": "https://data.mendeley.com/datasets/tywbtsjrjv/1",
        "licence": "CC0 1.0",
        "files": [("Plant_leaf_diseases_dataset_without_augmentation.zip", "https://data.mendeley.com/public-files/datasets/tywbtsjrjv/files/d5652a28-c1d8-4b76-97f3-72fb80f94efc/file_downloaded")],
    },
]


def expected_hashes(dataset_url: str) -> dict:
    dataset_id = dataset_url.rstrip("/").split("/")[-2]
    with open_url(f"https://data.mendeley.com/public-api/datasets/{dataset_id}") as r:
        data = json.load(r)
    return {f["filename"]: f.get("content_details", {}).get("sha256_hash") for f in data.get("files", [])}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    RAW.mkdir(parents=True, exist_ok=True)
    for source in SOURCES:
        hashes = expected_hashes(source["url"])
        for filename, url in source["files"]:
            target = RAW / source["key"] / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and hashes.get(filename) and sha256(target) == hashes[filename]:
                print(f"ok (cached)  {source['key']}/{filename}")
                continue
            print(f"downloading {source['key']}/{filename} ...", flush=True)
            tmp = target.with_suffix(target.suffix + ".part")
            with open_url(url, timeout=120) as response, open(tmp, "wb") as out:
                for block in iter(lambda: response.read(1 << 20), b""):
                    out.write(block)
            if hashes.get(filename) and sha256(tmp) != hashes[filename]:
                tmp.unlink()
                raise SystemExit(f"SHA-256 mismatch for {filename} — download discarded")
            tmp.replace(target)
            print(f"ok (verified) {source['key']}/{filename} {target.stat().st_size // 1_000_000} MB", flush=True)
    (RAW / "sources.json").write_text(json.dumps(SOURCES, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
