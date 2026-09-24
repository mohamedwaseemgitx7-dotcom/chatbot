"""Per-class and overall classification metrics (used by ai/training/evaluate_vision.py)."""
from sklearn.metrics import accuracy_score, precision_recall_fscore_support


def compute_metrics(gold, pred, labels):
    """gold/pred: sequences of class indices. Returns overall + per-class precision/recall/F1/support."""
    idx = list(range(len(labels)))
    p, r, f, s = precision_recall_fscore_support(gold, pred, labels=idx, zero_division=0)
    macro = precision_recall_fscore_support(gold, pred, labels=[i for i in idx if (s[i] > 0)], average="macro", zero_division=0)
    return {
        "accuracy": round(float(accuracy_score(gold, pred)), 4) if len(gold) else None,
        "macro_precision": round(float(macro[0]), 4),
        "macro_recall": round(float(macro[1]), 4),
        "macro_f1": round(float(macro[2]), 4),
        "images": int(len(gold)),
        "per_class": {labels[i]: {"precision": round(float(p[i]), 3), "recall": round(float(r[i]), 3), "f1": round(float(f[i]), 3),
                                  "support": int(s[i])} for i in idx if s[i] > 0},
    }
