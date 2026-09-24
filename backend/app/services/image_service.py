"""
Crop photo analysis:

  bytes → content check (JPEG/PNG/WEBP, ≤ 5 MB) → OpenCV decode + quality checks → vegetation check
        → MobileNetV3 (ONNX) → confidence gate → verified knowledge for the predicted condition → result

Outcomes (status):
  ok                 a supported crop/condition was identified with enough confidence
  uncertain          the photo was analysed but no supported crop/condition could be identified confidently
  model_unavailable  the vision model isn't trained/deployed — nothing is guessed
CPU-bound; call it from a threadpool.
"""
import logging
from typing import Any, Dict

from app.config.settings import get_settings
from app.embeddings.embedder import EmbeddingUnavailable, embed_one
from app.rag.response_engine import excerpt, sources_of
from app.rag.retriever import retrieve
from app.security.file_security import sniff_image
from app.vision.classifier import VisionModelUnavailable, classify, model_card
from app.vision.preprocess import InvalidImage, decode, plant_pixel_share, quality_problem, to_tensor

logger = logging.getLogger(__name__)

DISCLAIMER = ("This is a preliminary AI prediction from a photo, not a confirmed diagnosis. "
              "Confirm with your local agriculture officer before applying any pesticide or chemical.")
MIN_PLANT_SHARE = 0.02  # only rejects near-vegetation-free images (screenshots, documents); calibrated on held-out photos

MESSAGES = {
    "model_unavailable": "The image analysis model is not currently available.",
    "uncertain": "I could not confidently identify a supported crop or condition from this image.",
    "not_plant": "This photo doesn't look like a crop leaf. Please send a clear, close photo of one affected leaf.",
    "too_small": "This photo is too small to analyse. Please send a larger, closer photo of the leaf.",
    "too_dark": "This photo is too dark. Please take it again in daylight.",
    "too_bright": "This photo is too bright or washed out. Please take it again out of direct glare.",
    "too_blurry": "This photo is too blurry. Please hold the phone steady and take it again, close to the leaf.",
}


class UnsupportedImage(ValueError):
    """Raised for files that aren't a valid JPEG/PNG/WEBP image (→ HTTP 400)."""


# A knowledge record is only attached to a photo result if its title names the predicted condition —
# never "the nearest record for this crop" (that once attached caterpillar advice to early blight).
# Model class → words that must appear in the official knowledge record's title. Only classes with a matching
# TNAU record are listed; the others (e.g. tomato diseases, maize gray leaf spot) get no advice rather than wrong advice.
CONDITION_TITLE_KEYWORDS = {
    "rice_brown_spot": ["brown spot"],
    "rice_bacterial_leaf_blight": ["bacterial leaf blight"],
    "rice_leaf_blast": ["blast"],
    "banana_leaf_disease": ["sigatoka"],
    "maize_common_rust": ["common rust"],
    "maize_northern_leaf_blight": ["leaf blight"],
}


def _knowledge_for(class_name: str, crop: str, condition: str, healthy: bool) -> Dict[str, Any]:
    keywords = CONDITION_TITLE_KEYWORDS.get(class_name)
    if healthy or not keywords:
        return {"next_steps": [], "sources": []}
    try:
        vector = embed_one(f"{crop} {condition} symptoms management control")
    except EmbeddingUnavailable:
        return {"next_steps": [], "sources": []}
    hits = retrieve(vector, crop=crop, intent="crop_disease", top_k=10, threshold=0.0)
    records = [h.record for h in hits if any(k in h.record["title"].lower() for k in keywords)][:1]
    return {"next_steps": [excerpt(r["content"], 500) for r in records], "sources": sources_of(records)}


def analyze(data: bytes) -> Dict[str, Any]:
    settings = get_settings()
    if len(data) > settings.MAX_IMAGE_BYTES:
        raise UnsupportedImage("This photo is larger than 5 MB.")
    if sniff_image(data) is None:
        raise UnsupportedImage("Please upload a JPG, PNG or WEBP photo.")
    try:
        rgb = decode(data)
    except InvalidImage as error:
        raise UnsupportedImage(str(error)) from error

    card = model_card() or {}
    base = {"disclaimer": DISCLAIMER, "model_name": card.get("model_name"), "model_version": card.get("version"),
            "dataset_version": card.get("dataset_version")}

    problem = quality_problem(rgb)
    if problem:
        return {**base, "status": "uncertain", "reason": problem, "message": MESSAGES[problem]}
    if plant_pixel_share(rgb) < MIN_PLANT_SHARE:
        return {**base, "status": "uncertain", "reason": "not_plant", "message": MESSAGES["not_plant"]}

    try:
        ranked = classify(to_tensor(rgb))
    except VisionModelUnavailable:
        return {**base, "status": "model_unavailable", "message": MESSAGES["model_unavailable"]}

    best, confidence = ranked[0]
    alternatives = [{"crop": c["crop"], "condition": c["condition"], "confidence": round(p, 3)} for c, p in ranked if c.get("crop")]
    if best["name"] == "unsupported":
        return {**base, "status": "uncertain", "reason": "unsupported", "message": MESSAGES["uncertain"]}
    if confidence < settings.IMAGE_CONFIDENCE_THRESHOLD:
        return {**base, "status": "uncertain", "reason": "low_confidence", "message": MESSAGES["uncertain"],
                "top_predictions": alternatives}

    knowledge = _knowledge_for(best["name"], best["crop"], best["condition"], best.get("healthy", False))
    return {
        **base,
        "status": "ok",
        "crop": best["crop"],
        "prediction": best["condition"],
        "healthy": best.get("healthy", False),
        "confidence": round(confidence, 3),
        "top_predictions": alternatives,
        "possible_causes": [best["cause"]] if best.get("cause") else [],
        "recommended_next_steps": knowledge["next_steps"],
        "sources": knowledge["sources"],
    }
