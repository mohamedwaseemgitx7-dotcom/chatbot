"""
Crop-leaf condition classifier: MobileNetV3-Small fine-tuned on licensed agricultural datasets
(ai/training/train_vision.py), exported to ONNX and run with onnxruntime (no PyTorch at runtime).

models/vision/crop_disease.onnx   the network
models/vision/labels.json         class list + model card (datasets, licences, accuracy)
If either file is missing the model is reported as unavailable — predictions are never faked.
"""
import json
import logging
import threading
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "vision"

_lock = threading.Lock()
_session = None
_card: Optional[dict] = None


class VisionModelUnavailable(RuntimeError):
    pass


def model_card() -> Optional[dict]:
    path = MODEL_DIR / "labels.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def is_available() -> bool:
    return (MODEL_DIR / "crop_disease.onnx").exists() and (MODEL_DIR / "labels.json").exists()


def _load():
    global _session, _card
    if _session is not None:
        return
    with _lock:
        if _session is not None:
            return
        if not is_available():
            raise VisionModelUnavailable("vision model has not been trained")
        import onnxruntime as ort

        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        _session = ort.InferenceSession(str(MODEL_DIR / "crop_disease.onnx"), options, providers=["CPUExecutionProvider"])
        _card = model_card()


def classify(tensor: np.ndarray, top: int = 3) -> List[Tuple[dict, float]]:
    """[(class_info, probability)] best first. class_info: {name, crop, condition, healthy}."""
    _load()
    session, card = _session, _card
    if session is None or card is None:
        raise VisionModelUnavailable("vision model could not be loaded")
    logits = session.run(None, {session.get_inputs()[0].name: tensor})[0][0]
    exp = np.exp(logits - logits.max())
    probabilities = exp / exp.sum()
    order = np.argsort(probabilities)[::-1][:top]
    classes = card["classes"]
    return [(classes[i], float(probabilities[i])) for i in order]


def classify_disease(preprocessed_image) -> Tuple[str, str, float]:
    """Kept for callers of the old API."""
    info, p = classify(preprocessed_image, top=1)[0]
    return info["crop"], info["condition"], p
