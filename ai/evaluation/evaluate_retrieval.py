"""
Retrieval evaluation + threshold calibration (offline).

    backend/.venv/Scripts/python ai/evaluation/evaluate_retrieval.py

For every query in retrieval_queries.json it runs the same retriever the API uses (threshold 0 so every score
is visible), then reports hit@1 / hit@3 for answerable questions and the best score of questions that must get
no answer, and suggests the threshold that best separates them. Output: reports/retrieval_report.json.
"""
import json
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.embeddings.embedder import embed_one  # noqa: E402
from app.nlp.tanglish import to_english  # noqa: E402
from app.rag.retriever import retrieve, specific_terms  # noqa: E402

QUERIES = json.loads((Path(__file__).parent / "retrieval_queries.json").read_text(encoding="utf-8"))


def run(item, top_k=3):
    english = to_english(item["q"])
    vector = embed_one(english)
    terms = specific_terms(item["q"], english)
    language = item.get("language", "english")
    hits = retrieve(vector, crop=item.get("crop"), intent="crop_disease", top_k=top_k, threshold=-1.0, language=language, terms=terms)
    if language == "tamil" and not hits:
        hits = retrieve(vector, crop=item.get("crop"), intent="crop_disease", top_k=top_k, threshold=-1.0, terms=terms)
    return hits


def matches(record, item):
    title = record["title"].lower()
    return record["crop"] == item["crop"] and any(e.lower() in title for e in item["expect"])


def main():
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    rows, pos_scores, neg_scores = [], [], []
    for item in QUERIES["positive"]:
        hits = run(item)
        rank = next((i for i, h in enumerate(hits) if matches(h.record, item)), None)
        pos_scores.append(hits[rank].score if rank is not None else None)
        rows.append({"q": item["q"], "rank": rank, "top": hits[0].record["title"] if hits else None,
                     "top_score": round(hits[0].score, 3) if hits else None})
    for item in QUERIES["none"]:
        hits = run(item, top_k=1)
        neg_scores.append(hits[0].score if hits else -1.0)
        rows.append({"q": item["q"], "expected": "no answer", "top": hits[0].record["title"] if hits else None,
                     "top_score": round(hits[0].score, 3) if hits else None})

    # Served behaviour at the configured threshold (with the name-agreement rule): right, wrong, or no answer.
    from app.config.settings import get_settings
    from app.embeddings.embedder import embed_one as _e
    threshold = get_settings().RETRIEVAL_SIMILARITY_THRESHOLD
    served = {"right": 0, "wrong": 0, "no_answer": 0}
    wrong_examples = []
    for item in QUERIES["positive"]:
        english = to_english(item["q"])
        language = item.get("language", "english")
        kwargs = dict(crop=item.get("crop"), intent="crop_disease", top_k=1, terms=specific_terms(item["q"], english))
        hits = retrieve(_e(english), language=language, **kwargs) or ([] if language != "tamil" else retrieve(_e(english), **kwargs))
        if not hits:
            served["no_answer"] += 1
        elif matches(hits[0].record, item):
            served["right"] += 1
        else:
            served["wrong"] += 1
            wrong_examples.append({"q": item["q"], "answered_with": hits[0].record["title"]})
    refused = sum(1 for item in QUERIES["none"]
                  if not retrieve(_e(to_english(item["q"])), crop=item.get("crop"), intent="crop_disease", top_k=1,
                                  terms=specific_terms(item["q"], to_english(item["q"]))))

    found = [s for s in pos_scores if s is not None]
    best = max(
        (t / 100 for t in range(20, 80)),
        key=lambda t: sum(s >= t for s in found) + sum(s < t for s in neg_scores),
    )
    report = {
        "answerable_queries": len(pos_scores),
        "hit_at_1": sum(r.get("rank") == 0 for r in rows[: len(pos_scores)]) / len(pos_scores),
        "hit_at_3": sum(r.get("rank") is not None for r in rows[: len(pos_scores)]) / len(pos_scores),
        "suggested_threshold": best,
        "at_threshold": {
            "answerable_answered": sum(s >= best for s in found) / len(pos_scores),
            "unanswerable_refused": sum(s < best for s in neg_scores) / len(neg_scores),
        },
        "served_at_configured_threshold": {"threshold": threshold, **served, "unanswerable_refused": f"{refused}/{len(QUERIES['none'])}",
                                           "wrong_examples": wrong_examples},
        "rows": rows,
    }
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "retrieval_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
    for r in rows:
        print(f"  {r['q'][:44]:46} rank={r.get('rank', r.get('expected'))!s:10} score={r['top_score']}  top={str(r['top'])[:50]}")


if __name__ == "__main__":
    main()
