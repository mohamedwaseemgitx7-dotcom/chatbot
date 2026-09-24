"""
Offline training of the intent classifier (never run inside the API).

    backend/.venv/Scripts/python ai/training/train_intent.py

Data: datasets/nlp/farmer_queries.csv (group-aware train/validation/test split) plus, for training only,
positive intent_examples, noisy spelling variations and out_of_domain_queries. Augmentation rows that are
near-duplicates (char-ngram cosine ≥ 0.9) of any validation/test query are dropped to prevent leakage.

Model: [char 2–5-gram TF-IDF of the cleaned text] + [word 1–2-gram TF-IDF of the English-normalised text]
+ [MiniLM sentence embedding of the English-normalised text] → multinomial logistic regression.
The embedding view lets the classifier generalise to phrasings it never saw (few seeds per intent). C is picked on validation; the test split is scored once at the end.
Output: backend/models/intent/intent_model.joblib and reports/intent_report.json.
"""
import csv
import hashlib
import json
import io
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.nlp.language_detector import detect_language  # noqa: E402
from app.nlp.normalizer import clean_text  # noqa: E402
from app.embeddings.embedder import embed  # noqa: E402
from app.nlp.tanglish import to_english  # noqa: E402
from scipy.sparse import csr_matrix  # noqa: E402

DATA = ROOT / "datasets" / "nlp"
OUT = ROOT / "backend" / "models" / "intent"
REPORTS = ROOT / "reports"


def read(name):
    with open(DATA / name, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def hashed_split(text: str) -> str:
    """Deterministic 70/15/15 split for files without one."""
    bucket = int(hashlib.sha1(text.encode()).hexdigest(), 16) % 100
    return "train" if bucket < 70 else "validation" if bucket < 85 else "test"


def load():
    rows = {"train": [], "validation": [], "test": []}
    for r in read("farmer_queries.csv"):
        rows[r["split"]].append((r["text"], r["intent"], r["language"]))

    extra = []
    for r in read("intent_examples.csv"):
        if r["split"] == "train" and r["label"] == "positive":
            extra.append((r["text"], r["intent"], r["language"]))
        elif r["split"] == "train" and r["true_intent"] == "out_of_domain":
            extra.append((r["text"], "out_of_domain", r["language"]))
    for r in read("spelling_variations.csv"):
        if r["split"] == "train" and r["intent"]:
            extra.append((r["noisy_text"], r["intent"], r["language"]))
    # intents.json: hand-written examples per language + keywords (short keyword queries are realistic).
    for item in json.loads((DATA / "intents.json").read_text(encoding="utf-8")):
        for lang, examples in (item.get("examples") or {}).items():
            extra.extend((text, item["intent_name"], lang) for text in examples)
        extra.extend((kw, item["intent_name"], "keyword") for kw in item.get("keywords", []) if len(kw) > 2)
    for r in read("out_of_domain_queries.csv"):
        split = hashed_split(r["text"])
        (rows[split] if split != "train" else extra).append((r["text"], "out_of_domain", r["language"]))
    return rows, extra


def drop_leaks(extra, held_out):
    """Removes augmentation rows that nearly duplicate any validation/test query."""
    probe = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5)).fit([clean_text(t) for t, *_ in held_out + extra])
    held = probe.transform([clean_text(t) for t, *_ in held_out])
    kept, dropped = [], 0
    for start in range(0, len(extra), 2000):
        chunk = extra[start : start + 2000]
        sims = cosine_similarity(probe.transform([clean_text(t) for t, *_ in chunk]), held).max(axis=1)
        for row, sim in zip(chunk, sims):
            if sim >= 0.9:
                dropped += 1
            else:
                kept.append(row)
    return kept, dropped


def dedupe(rows):
    seen, out = set(), []
    for text, intent, lang in rows:
        key = (clean_text(text), intent)
        if key not in seen:
            seen.add(key)
            out.append((text, intent, lang))
    return out


EMBEDDING_WEIGHT = 1.5  # scales the dense view relative to the TF-IDF views


class Features:
    def __init__(self):
        self.char = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2, max_features=60000)
        self.word = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True, min_df=1, token_pattern=r"(?u)\b\w+\b")

    @staticmethod
    def views(texts):
        return [clean_text(t) for t in texts], [to_english(t) for t in texts]

    @staticmethod
    def dense(eng):
        return csr_matrix(np.vstack([embed(eng[i : i + 256]) for i in range(0, len(eng), 256)]) * EMBEDDING_WEIGHT)

    def fit_transform(self, texts):
        raw, eng = self.views(texts)
        return hstack([self.char.fit_transform(raw), self.word.fit_transform(eng), self.dense(eng)]).tocsr()

    def transform(self, texts):
        raw, eng = self.views(texts)
        return hstack([self.char.transform(raw), self.word.transform(eng), self.dense(eng)]).tocsr()


def evaluate(model, feats, rows):
    texts = [t for t, *_ in rows]
    gold = [i for _, i, _ in rows]
    pred = model.predict(feats.transform(texts))
    return pred, gold, accuracy_score(gold, pred), f1_score(gold, pred, average="macro")


def main():
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    rows, extra = load()
    extra, leaked = drop_leaks(extra, rows["validation"] + rows["test"])
    train = dedupe(rows["train"] + extra)
    print(f"train {len(train)} (augmentation leaks dropped: {leaked}) | validation {len(rows['validation'])} | test {len(rows['test'])}")

    feats = Features()
    X = feats.fit_transform([t for t, *_ in train])
    y = [i for _, i, _ in train]

    best = None
    for C in (2.0, 5.0, 10.0, 20.0):
        model = LogisticRegression(C=C, max_iter=3000, class_weight="balanced")
        model.fit(X, y)
        _, _, acc, f1 = evaluate(model, feats, rows["validation"])
        print(f"  C={C:<5} validation acc {acc:.3f} macro-F1 {f1:.3f}")
        if best is None or f1 > best[0]:
            best = (f1, C, model)
    assert best is not None  # the C grid above is never empty
    _, C, model = best

    pred, gold, acc, f1 = evaluate(model, feats, rows["test"])
    by_lang, per_intent = defaultdict(list), defaultdict(list)
    for (text, intent, lang), p in zip(rows["test"], pred):
        by_lang[lang].append(p == intent)
        per_intent[intent].append(p == intent)
    ood_gold = [g == "out_of_domain" for g in gold]
    ood_pred = [p == "out_of_domain" for p in pred]
    ood_recall = sum(a and b for a, b in zip(ood_gold, ood_pred)) / max(1, sum(ood_gold))
    ood_false_alarm = sum(b and not a for a, b in zip(ood_gold, ood_pred)) / max(1, len(gold) - sum(ood_gold))

    report = {
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "C": C,
        "train_rows": len(train),
        "augmentation_leaks_dropped": leaked,
        "test_rows": len(gold),
        "test_accuracy": round(acc, 3),
        "test_macro_f1": round(f1, 3),
        "test_accuracy_by_language": {k: round(float(np.mean(v)), 3) for k, v in sorted(by_lang.items())},
        "out_of_domain_recall": round(ood_recall, 3),
        "out_of_domain_false_alarm_rate": round(ood_false_alarm, 3),
        "weakest_intents": dict(sorted(((k, round(float(np.mean(v)), 2)) for k, v in per_intent.items()), key=lambda kv: kv[1])[:8]),
        "baseline_before_this_work": {"test_accuracy": 0.602, "test_macro_f1": 0.566, "note": "dataset baseline, TF-IDF only"},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    joblib.dump({"char": feats.char, "word": feats.word, "embedding_weight": EMBEDDING_WEIGHT, "model": model,
                 "labels": list(model.classes_), "report": report},
                OUT / "intent_model.joblib", compress=3)
    (REPORTS / "intent_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
