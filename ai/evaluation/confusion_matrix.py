"""Confusion matrix as CSV + the most frequent mistakes (used by ai/training/evaluate_vision.py)."""
import csv
from collections import Counter

import numpy as np


def confusion(gold, pred, labels):
    matrix = np.zeros((len(labels), len(labels)), dtype=int)
    for g, p in zip(gold, pred):
        matrix[g, p] += 1
    return matrix


def write_csv(matrix, labels, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["true \\ predicted", *labels])
        for label, row in zip(labels, matrix):
            writer.writerow([label, *row.tolist()])


def top_confusions(gold, pred, labels, n=10):
    counts = Counter((labels[g], labels[p]) for g, p in zip(gold, pred) if g != p)
    return [{"true": a, "predicted": b, "count": c} for (a, b), c in counts.most_common(n)]
