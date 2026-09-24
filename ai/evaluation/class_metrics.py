"""Per-class and overall classification metrics (used by ai/training/evaluate_vision.py)."""
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support


def compute_metrics(gold, pred, labels):
    """gold/pred: sequences of class indices. Returns overall + per-class precision/recall/F1/support."""
    idx = list(range(len(labels)))
    p, r, f, s = (np.asarray(v) for v in precision_recall_fscore_support(gold, pred, labels=idx, zero_division=0))
    macro = [float(np.asarray(v)) for v in precision_recall_fscore_support(
        gold, pred, labels=[i for i in idx if s[i] > 0], average="macro", zero_division=0)[:3]]
    return {
        "accuracy": round(float(accuracy_score(gold, pred)), 4) if len(gold) else None,
        "macro_precision": round(macro[0], 4),
        "macro_recall": round(macro[1], 4),
        "macro_f1": round(macro[2], 4),
        "images": int(len(gold)),
        "per_class": {labels[i]: {"precision": round(float(p[i]), 3), "recall": round(float(r[i]), 3), "f1": round(float(f[i]), 3),
                                  "support": int(s[i])} for i in idx if s[i] > 0},
    }
