"""
Step 3 of the knowledge pipeline: remove duplicates and pair English ↔ Tamil versions of the same page.

    python scripts/deduplicate.py      (data/processed/knowledge.jsonl → data/processed/knowledge_dedup.jsonl)

- exact duplicates: identical normalised content
- near duplicates: char-n-gram TF-IDF cosine ≥ 0.92 within the same crop + language (first kept)
- pairing: TNAU's Tamil pages live under /ta/ with a "_ta"/"_tamain" suffix; when the matching English
  page exists, both get the same pair_id so a Tamil question can be answered with the official Tamil text.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "processed" / "knowledge.jsonl"
OUT = ROOT / "data" / "processed" / "knowledge_dedup.jsonl"
REPORT = ROOT / "data" / "processed" / "dedup_report.json"
NEAR_DUPLICATE = 0.92


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w஀-௿ ]", " ", text.lower())).strip()


def english_url_for(tamil_url: str) -> str:
    url = tamil_url.replace("/ta/", "/", 1)
    url = re.sub(r"_tamain\.html$", "main.html", url)
    url = re.sub(r"_ta\.html$", ".html", url)
    return url


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    records = [json.loads(l) for l in IN.read_text(encoding="utf-8").splitlines() if l.strip()]
    stats = Counter(input=len(records))

    seen, unique = set(), []
    for r in records:
        key = (r["language"], norm(r["content"]))
        if key in seen:
            stats["exact_duplicates"] += 1
            continue
        seen.add(key)
        unique.append(r)

    groups = defaultdict(list)
    for i, r in enumerate(unique):
        groups[(r["crop"], r["language"])].append(i)
    drop = set()
    for idx in groups.values():
        if len(idx) < 2:
            continue
        texts = [norm(unique[i]["content"]) for i in idx]
        sims = cosine_similarity(TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5)).fit_transform(texts))
        for a in range(len(idx)):
            if idx[a] in drop:
                continue
            for b in range(a + 1, len(idx)):
                if sims[a, b] >= NEAR_DUPLICATE:
                    drop.add(idx[b])
    stats["near_duplicates"] = len(drop)
    kept = [r for i, r in enumerate(unique) if i not in drop]

    by_url = {r["source_url"]: r for r in kept if r["language"] == "english"}
    for r in kept:
        if r["language"] == "english":
            r["pair_id"] = r["id"]
    for r in kept:
        if r["language"] == "tamil":
            match = by_url.get(english_url_for(r["source_url"]))
            r["pair_id"] = match["id"] if match else None
            stats["tamil_paired" if match else "tamil_unpaired"] += 1

    with open(OUT, "w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    stats["output"] = len(kept)
    REPORT.write_text(json.dumps(dict(stats), indent=2), encoding="utf-8")
    print(json.dumps(dict(stats), indent=2))


if __name__ == "__main__":
    main()
