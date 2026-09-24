"""
In-memory vector stores over the verified knowledge base (NumPy cosine similarity — no external DB).

Files (built offline by scripts/build_knowledge_index.py):
  models/knowledge/knowledge.jsonl         verified records (English first, then official Tamil)
  models/knowledge/embeddings.npy          float32 (n_english, 384), aligned with the English records
  models/knowledge/embeddings_tamil.npy    float32 (n_tamil, 384), aligned with the Tamil records
"""
import json
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "models" / "knowledge"

_lock = threading.Lock()
_stores: Optional[Dict[str, "KnowledgeStore"]] = None


class KnowledgeStore:
    def __init__(self, records: List[dict], vectors: np.ndarray):
        self.records = records
        self.vectors = vectors
        self.crops = np.array([r.get("crop", "") for r in records])
        self.topics = np.array([r.get("topic", "") for r in records])
        # Lower-case titles with spaces removed too, so "குலை" matches "குலைநோய்" and "stemborer" matches "stem borer".
        self.titles = [(r.get("title", "") + " " + r.get("title", "").replace(" ", "")).lower() for r in records]
        # Kept for compatibility: explicit English↔Tamil pairs (rare — see deduplicate.py).
        self.tamil_by_pair: Dict[str, dict] = {}


def _load_all() -> Dict[str, "KnowledgeStore"]:
    global _stores
    if _stores is not None:
        return _stores
    with _lock:
        if _stores is not None:
            return _stores
        stores: Dict[str, KnowledgeStore] = {}
        records_path = KNOWLEDGE_DIR / "knowledge.jsonl"
        if records_path.exists():
            records = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            for language, file in (("english", "embeddings.npy"), ("tamil", "embeddings_tamil.npy")):
                subset = [r for r in records if r.get("language") == language]
                path = KNOWLEDGE_DIR / file
                if not subset or not path.exists():
                    continue
                vectors = np.load(path).astype(np.float32)
                if len(vectors) != len(subset):
                    logger.error("Knowledge index mismatch (%s): %d records vs %d vectors", language, len(subset), len(vectors))
                    continue
                stores[language] = KnowledgeStore(subset, vectors)
            if "english" in stores:
                stores["english"].tamil_by_pair = {r["pair_id"]: r for r in records if r.get("language") == "tamil" and r.get("pair_id")}
        if not stores:
            logger.warning("Knowledge index not built (%s)", KNOWLEDGE_DIR)
        else:
            logger.info("Knowledge index loaded: %s", {k: len(v.records) for k, v in stores.items()})
        _stores = stores
        return _stores


def load_store(language: str = "english") -> Optional[KnowledgeStore]:
    """The searchable store for a language, or None when the index hasn't been built."""
    return _load_all().get(language)


def record_count() -> int:
    return sum(len(s.records) for s in _load_all().values())
