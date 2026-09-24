"""
Evaluates the committed intent model (backend/models/intent/intent_model.joblib) without retraining.

    backend/.venv/Scripts/python ai/evaluation/evaluate_intent.py

Uses the held-out test split of datasets/nlp/farmer_queries.csv and the same feature code as the API.
Prints accuracy, macro-F1, per-language accuracy, out-of-domain recall and the weakest intents.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.nlp.intent_classifier import predict_intents  # noqa: E402
from app.nlp.tanglish import to_english  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    from sklearn.metrics import f1_score

    with open(ROOT / "datasets" / "nlp" / "farmer_queries.csv", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["split"] == "test"]
    gold, pred, by_lang, per_intent = [], [], defaultdict(list), defaultdict(list)
    for r in rows:
        p = predict_intents(r["text"], to_english(r["text"]), top=1)[0][0]
        gold.append(r["intent"]), pred.append(p)
        by_lang[r["language"]].append(p == r["intent"])
        per_intent[r["intent"]].append(p == r["intent"])
    ood = [p == "out_of_domain" for g, p in zip(gold, pred) if g == "out_of_domain"]
    report = {
        "test_rows": len(rows),
        "accuracy": round(sum(g == p for g, p in zip(gold, pred)) / len(rows), 3),
        "macro_f1": round(f1_score(gold, pred, average="macro"), 3),
        "accuracy_by_language": {k: round(sum(v) / len(v), 3) for k, v in sorted(by_lang.items())},
        "out_of_domain_recall": round(sum(ood) / len(ood), 3) if ood else None,
        "weakest_intents": dict(sorted(((k, round(sum(v) / len(v), 2)) for k, v in per_intent.items()), key=lambda kv: kv[1])[:8]),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
