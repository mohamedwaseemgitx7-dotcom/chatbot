"""
Step 5 of the knowledge pipeline: embeddings for the API's vector search.

    backend/.venv/Scripts/python scripts/build_knowledge_index.py

Reads data/verified/knowledge.jsonl and embeds every record with the same ONNX MiniLM model the API uses.
English records are embedded directly; official Tamil records are embedded through the same Tamil→English
normaliser applied to questions, so Tamil questions can be answered with the official Tamil text.
Writes backend/models/knowledge/{knowledge.jsonl, embeddings.npy, embeddings_tamil.npy}.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.embeddings.embedder import embed  # noqa: E402
from app.nlp.tanglish import to_english  # noqa: E402

IN = ROOT / "data" / "verified" / "knowledge.jsonl"
OUT = ROOT / "backend" / "models" / "knowledge"
MARKUP = re.compile(r"\*\*|^- ", re.M)


def text_for_embedding(r: dict) -> str:
    body = MARKUP.sub("", r["content"])
    if r["language"] == "tamil":
        return f"{r['crop']} {r['topic']}: {to_english(r['title'])}. {to_english(body[:800])}"
    return f"{r['crop']} {r['topic']}: {r['title']}. {body}"


def embed_all(records):
    if not records:
        return np.zeros((0, 384), dtype=np.float32)
    return np.vstack([embed([text_for_embedding(r) for r in records[i : i + 64]]) for i in range(0, len(records), 64)])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    records = [json.loads(l) for l in IN.read_text(encoding="utf-8").splitlines() if l.strip()]
    english = [r for r in records if r["language"] == "english"]
    tamil = [r for r in records if r["language"] == "tamil"]
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "knowledge.jsonl", "w", encoding="utf-8") as f:
        for r in english + tamil:  # row i of embeddings.npy ↔ i-th English record; same for Tamil
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    np.save(OUT / "embeddings.npy", embed_all(english).astype(np.float32))
    np.save(OUT / "embeddings_tamil.npy", embed_all(tamil).astype(np.float32))
    print(f"{len(english)} English + {len(tamil)} Tamil records embedded → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
