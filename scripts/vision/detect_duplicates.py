"""
Step 4 — exact and near-duplicate detection, label-conflict detection.

    backend/.venv/Scripts/python scripts/vision/detect_duplicates.py   → metadata/duplicates.csv

- exact duplicates: identical file bytes (SHA-1)
- near duplicates: difference-hash Hamming distance ≤ NEAR_DUP_BITS (re-encoded, resized, augmented copies)
Images are joined into groups (union-find). Splits later keep a whole group on one side, so no copy of a
photo can appear in both train and test. A group spanning several labels is a label conflict and is dropped.
"""
import sys
from collections import defaultdict

import numpy as np

from common import METADATA, read_csv, write_csv

NEAR_DUP_BITS = 4


class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    rows = read_csv(METADATA / "candidates.csv")
    n = len(rows)
    uf = UnionFind(n)

    exact = 0
    by_sha = defaultdict(list)
    for i, r in enumerate(rows):
        by_sha[r["sha1"]].append(i)
    for idx in by_sha.values():
        for j in idx[1:]:
            uf.union(idx[0], j)
            exact += 1

    hashes = np.array([int(r["dhash"], 16) for r in rows], dtype=np.uint64)
    near_pairs = 0
    for start in range(0, n, 2048):
        block = hashes[start : start + 2048]
        dist = np.bitwise_count(block[:, None] ^ hashes[None, :])
        a, b = np.nonzero(dist <= NEAR_DUP_BITS)
        for i, j in zip(a + start, b):
            if i < j and rows[i]["sha1"] != rows[j]["sha1"]:
                uf.union(int(i), int(j))
                near_pairs += 1

    groups = defaultdict(list)
    for i in range(n):
        groups[uf.find(i)].append(i)
    conflicts = 0
    out = []
    for gid, members in groups.items():
        labels = {rows[i]["label"] for i in members}
        conflict = len(labels) > 1
        conflicts += conflict
        seen_sha = set()
        for i in members:
            dup = rows[i]["sha1"] in seen_sha
            seen_sha.add(rows[i]["sha1"])
            out.append({**rows[i], "group_id": f"g{gid}", "group_size": len(members),
                        "exact_duplicate": dup, "label_conflict": conflict})
    write_csv(METADATA / "duplicates.csv", out)
    stats = {"images": n, "exact_duplicates": exact, "near_duplicate_pairs": near_pairs,
             "groups": len(groups), "label_conflict_groups": conflicts}
    (METADATA / "duplicate_stats.json").write_text(__import__("json").dumps(stats, indent=2), encoding="utf-8")
    print(stats)


if __name__ == "__main__":
    main()
