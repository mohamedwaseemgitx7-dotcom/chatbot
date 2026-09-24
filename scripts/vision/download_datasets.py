"""
Step 1 — download + licence validation + extraction.

    backend/.venv/Scripts/python scripts/vision/download_datasets.py

- refuses any source whose licence is not in ALLOWED_LICENSES
- Mendeley files are verified against the SHA-256 published by Mendeley; others get their hash recorded
- extracts each archive once into datasets/vision/raw/<source>/extracted (Windows tar reads zip/rar/7z)
- writes metadata/sources.csv and metadata/licenses.csv
"""
import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

from common import ALLOWED_LICENSES, METADATA, RAW, SOURCES, USER_AGENT, extracted_dir, read_csv, sha256_file, write_csv

TAR = r"C:\Windows\System32\tar.exe" if sys.platform == "win32" else "bsdtar"


def open_url(url, timeout=120):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=timeout)


def mendeley_files(dataset_id: str) -> dict:
    with open_url(f"https://data.mendeley.com/public-api/datasets/{dataset_id}") as r:
        data = json.load(r)
    return {f["filename"]: f.get("content_details", {}) for f in data.get("files", [])}


def resolve(url: str, filename: str, kind):
    """(download_url, expected_sha256) — Mendeley URLs/hashes are looked up from its public API."""
    if kind != "mendeley":
        return url, None
    dataset_id = url.split(":", 1)[1] if url.startswith("MENDELEY:") else url.split("/datasets/")[1].split("/")[0]
    details = mendeley_files(dataset_id).get(filename, {})
    return (details.get("download_url") or url), details.get("sha256_hash")


def download(url: str, target, expected_sha: str | None) -> str:
    if target.exists() and (expected_sha is None or sha256_file(target) == expected_sha):
        print(f"  cached   {target.name}")
        return sha256_file(target)
    print(f"  download {target.name} ...", flush=True)
    tmp = target.with_suffix(target.suffix + ".part")
    with open_url(url, timeout=300) as response, open(tmp, "wb") as out:
        for block in iter(lambda: response.read(1 << 20), b""):
            out.write(block)
    digest = sha256_file(tmp)
    if expected_sha and digest != expected_sha:
        tmp.unlink()
        raise SystemExit(f"SHA-256 mismatch for {target.name} — download discarded")
    tmp.replace(target)
    return digest


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    previous = {r["dataset_key"] + r["file"]: r for r in read_csv(METADATA / "sources.csv")} if (METADATA / "sources.csv").exists() else {}
    rows, licences = [], []
    for key, source in SOURCES.items():
        if source["license"] not in ALLOWED_LICENSES:
            raise SystemExit(f"{key}: licence {source['license']!r} is not approved — not downloading")
        print(f"{key} ({source['license']})")
        folder = RAW / key
        folder.mkdir(parents=True, exist_ok=True)
        for filename, url, kind in source["files"]:
            download_url, expected = resolve(url, filename, kind)
            digest = download(download_url, folder / filename, expected)
            out = extracted_dir(key)
            marker = out / f".extracted-{filename}"
            if not marker.exists():
                out.mkdir(parents=True, exist_ok=True)
                subprocess.run([TAR, "-xf", str(folder / filename), "-C", str(out)], check=True)
                marker.write_text(digest, encoding="utf-8")
            old = previous.get(key + filename, {})
            rows.append({
                "dataset_key": key, "dataset_name": source["dataset_name"], "file": filename, "source_url": source["source_url"],
                "sha256": digest, "verified_against_publisher_hash": bool(expected),
                "download_date": old.get("download_date") or datetime.now(timezone.utc).date().isoformat(),
                "image_style": source["image_style"],
            })
        licences.append({"dataset_key": key, "dataset_name": source["dataset_name"], "license": source["license"],
                         "license_url": source["license_url"], "citation": source["citation"],
                         "usage_restrictions": source["usage_restrictions"]})
    write_csv(METADATA / "sources.csv", rows)
    write_csv(METADATA / "licenses.csv", licences)
    print(f"{len(rows)} files ready; metadata/sources.csv and metadata/licenses.csv written")


if __name__ == "__main__":
    main()
