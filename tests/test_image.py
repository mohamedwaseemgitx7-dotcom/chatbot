import csv
from pathlib import Path

import pytest

from app.vision import classifier

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "datasets" / "vision" / "metadata" / "manifest.csv"
TEST_DIR = ROOT / "datasets" / "vision" / "test"


def held_out_photo(row):
    return (TEST_DIR / row["label"] / f"{row['image_id']}.jpg").read_bytes()


def analyze(client, data, name="leaf.png", mime="image/png"):
    return client.post("/api/image/analyze", files={"file": (name, data, mime)})


@pytest.mark.parametrize("data, name, mime", [
    (b"MZ\x90\x00this is an executable", "leaf.png", "image/png"),     # disguised .exe
    (b"#!/bin/sh\nrm -rf /\n", "leaf.jpg", "image/jpeg"),              # script
    (b"%PDF-1.7 not an image", "leaf.webp", "image/webp"),
    (b"", "empty.png", "image/png"),
])
def test_non_images_are_rejected(client, data, name, mime):
    response = analyze(client, data, name, mime)
    assert response.status_code == 400
    assert "stack" not in response.text.lower()


def test_oversized_upload_is_rejected(client):
    response = analyze(client, b"\x89PNG\r\n\x1a\n" + b"0" * (5 * 1024 * 1024 + 10))
    assert response.status_code == 413


def test_corrupt_image_with_valid_header_is_rejected(client):
    assert analyze(client, b"\x89PNG\r\n\x1a\n" + b"garbage" * 100).status_code == 400


def test_tiny_image_is_uncertain_not_forced(client, make_png):
    body = analyze(client, make_png(20, 20)).json()
    assert body["status"] == "uncertain" and body["reason"] == "too_small"


def test_non_plant_photo_is_uncertain(client, make_png):
    body = analyze(client, make_png(300, 300, color=(30, 30, 200))).json()  # plain blue picture
    assert body["status"] == "uncertain"
    assert "crop" not in body and "prediction" not in body


def test_model_missing_is_reported_honestly(client, make_png, monkeypatch):
    monkeypatch.setattr("app.services.image_service.classify",
                        lambda tensor: (_ for _ in ()).throw(classifier.VisionModelUnavailable("x")))
    body = analyze(client, make_png()).json()
    assert body["status"] == "model_unavailable"
    assert "prediction" not in body and "confidence" not in body


@pytest.mark.skipif(not classifier.is_available() or not MANIFEST.exists() or not TEST_DIR.exists(),
                    reason="vision model or local test images missing (build with scripts/vision/build_dataset.py)")
def test_real_model_predicts_held_out_images(client):
    """Held-out test-split photos (never seen in training) are analysed by the actual ONNX model."""
    with open(MANIFEST, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["split"] == "test"]
    by_label = {}
    for r in rows:
        by_label.setdefault(r["label"], r)
    card = classifier.model_card()
    assert card is not None
    names = {c["name"]: c for c in card["classes"]}
    correct = 0
    for label, row in by_label.items():
        if label == "unsupported":
            continue
        body = analyze(client, held_out_photo(row), "photo.jpg", "image/jpeg").json()
        assert body["status"] in {"ok", "uncertain"}
        if body["status"] == "ok":
            assert 0 <= body["confidence"] <= 1
            correct += body["crop"] == names[label]["crop"] and body["prediction"] == names[label]["condition"]
    assert correct >= (len(by_label) - 1) * 0.7


@pytest.mark.skipif(not classifier.is_available() or not MANIFEST.exists() or not TEST_DIR.exists(),
                    reason="vision model or local test images missing (build with scripts/vision/build_dataset.py)")
def test_attached_knowledge_is_about_the_predicted_condition(client):
    """Regression: an early-blight photo once came back with caterpillar advice (nearest record, wrong topic)."""
    from app.services.image_service import CONDITION_TITLE_KEYWORDS

    with open(MANIFEST, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["split"] == "test" and r["label"] in CONDITION_TITLE_KEYWORDS]
    seen = set()
    for row in rows:
        if row["label"] in seen:
            continue
        seen.add(row["label"])
        body = analyze(client, held_out_photo(row), "photo.jpg", "image/jpeg").json()
        if body["status"] != "ok":
            continue
        card = classifier.model_card()
        assert card is not None
        keywords = CONDITION_TITLE_KEYWORDS.get(next(c["name"] for c in card["classes"]
                                                    if c["crop"] == body["crop"] and c["condition"] == body["prediction"]), [])
        for source in body.get("sources", []):
            assert any(k in source["title"].lower() for k in keywords), (body["prediction"], source["title"])
