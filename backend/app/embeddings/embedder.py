"""
Sentence embeddings (all-MiniLM-L6-v2, int8 ONNX) on onnxruntime — no PyTorch at runtime.

Loaded lazily on first use and shared by every request. Inputs should be English-normalised text
(see app.nlp.tanglish.to_english), because the model is English-only.
"""
import logging
import threading
from pathlib import Path
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "embedding"
MAX_TOKENS = 128
DIMENSIONS = 384

_lock = threading.Lock()
_session = None
_tokenizer = None
_unavailable: Optional[str] = None


class EmbeddingUnavailable(RuntimeError):
    pass


def _load():
    global _session, _tokenizer, _unavailable
    if _session is not None:
        return
    with _lock:
        if _session is not None:
            return
        if _unavailable:
            raise EmbeddingUnavailable(_unavailable)
        try:
            import onnxruntime as ort
            from tokenizers import Tokenizer

            tokenizer = Tokenizer.from_file(str(MODEL_DIR / "tokenizer.json"))
            tokenizer.enable_truncation(max_length=MAX_TOKENS)
            tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
            options = ort.SessionOptions()
            options.intra_op_num_threads = 2
            options.inter_op_num_threads = 1
            session = ort.InferenceSession(str(MODEL_DIR / "model.onnx"), options, providers=["CPUExecutionProvider"])
        except Exception as error:  # missing files / incompatible CPU: report once, never crash the API
            _unavailable = f"embedding model unavailable ({type(error).__name__})"
            logger.error("Could not load embedding model from %s: %s", MODEL_DIR, error)
            raise EmbeddingUnavailable(_unavailable) from error
        _tokenizer, _session = tokenizer, session


def embed(texts: List[str]) -> np.ndarray:
    """L2-normalised float32 embeddings, shape (len(texts), 384)."""
    _load()
    if not texts:
        return np.zeros((0, DIMENSIONS), dtype=np.float32)
    encodings = _tokenizer.encode_batch(texts)
    ids = np.array([e.ids for e in encodings], dtype=np.int64)
    mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
    feeds = {"input_ids": ids, "attention_mask": mask}
    if "token_type_ids" in {i.name for i in _session.get_inputs()}:
        feeds["token_type_ids"] = np.zeros_like(ids)
    token_vectors = _session.run(None, feeds)[0]  # (batch, tokens, 384)
    weights = mask[..., None].astype(np.float32)
    pooled = (token_vectors * weights).sum(axis=1) / np.clip(weights.sum(axis=1), 1e-9, None)
    return (pooled / np.clip(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-9, None)).astype(np.float32)


def embed_one(text: str) -> np.ndarray:
    return embed([text])[0]


def is_available() -> bool:
    return (MODEL_DIR / "model.onnx").exists() and (MODEL_DIR / "tokenizer.json").exists() and not _unavailable
