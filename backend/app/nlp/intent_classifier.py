"""
Intent classifier: char + word TF-IDF and a MiniLM sentence embedding → logistic regression.
Trained offline by ai/training/train_intent.py; this module only loads the artifact (lazily, once).
"""
import logging
import threading
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from scipy.sparse import csr_matrix, hstack

from app.embeddings.embedder import embed
from app.nlp.normalizer import clean_text

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "intent" / "intent_model.joblib"

_lock = threading.Lock()
_artifact = None


class IntentModelUnavailable(RuntimeError):
    pass


def _load():
    global _artifact
    if _artifact is None:
        with _lock:
            if _artifact is None:
                if not MODEL_PATH.exists():
                    raise IntentModelUnavailable("intent model has not been trained")
                import joblib

                _artifact = joblib.load(MODEL_PATH)
    return _artifact


def is_available() -> bool:
    return MODEL_PATH.exists()


def predict_intents(text: str, english: str, embedding: Optional[np.ndarray] = None, top: int = 3) -> List[Tuple[str, float]]:
    """Top intents with probabilities. `english` is the normalised text; `embedding` may be reused."""
    artifact = _load()
    vector = embedding if embedding is not None else embed([english])[0]
    features = hstack([
        artifact["char"].transform([clean_text(text)]),
        artifact["word"].transform([english]),
        csr_matrix(vector[None, :] * artifact.get("embedding_weight", 1.0)),
    ]).tocsr()
    probabilities = artifact["model"].predict_proba(features)[0]
    order = np.argsort(probabilities)[::-1][:top]
    return [(artifact["labels"][i], float(probabilities[i])) for i in order]


def predict_intent(text: str, english: str = "") -> Tuple[str, float]:
    """Kept for callers of the old API."""
    from app.nlp.tanglish import to_english

    return predict_intents(text, english or to_english(text), top=1)[0]
