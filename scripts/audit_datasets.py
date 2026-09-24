"""
Dataset audit (read-only): writes reports/dataset_audit.json and reports/dataset_audit.md.

    backend/.venv/Scripts/python scripts/audit_datasets.py

Checks the NLP training data (duplicates, near-duplicates across splits, missing values, label validity,
language/intent balance, script consistency) and the knowledge sources (what is sourced vs synthetic).
Nothing is deleted — problems are reported for review.
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "datasets"
REPORTS = ROOT / "reports"


def read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def tamil_share(text):
    letters = re.findall(r"[a-zA-Z஀-௿]", text)
    return sum("஀" <= c <= "௿" for c in letters) / max(1, len(letters))


def norm(text):
    return re.sub(r"\s+", " ", re.sub(r"[^\w஀-௿ ]", " ", text.lower())).strip()


def audit_queries():
    rows = read_csv(DATASETS / "nlp" / "farmer_queries.csv")
    intents = {i["intent_name"] for i in json.loads((DATASETS / "nlp" / "intents.json").read_text(encoding="utf-8"))}
    required = ["id", "text", "language", "intent", "split"]
    missing = {k: sum(1 for r in rows if not r.get(k, "").strip()) for k in required}
    exact_dupes = sum(n - 1 for n in Counter((norm(r["text"]), r["intent"]) for r in rows).values() if n > 1)
    conflicting = [t for t, labels in _labels_by_text(rows).items() if len(labels) > 1]
    unknown_intents = sorted({r["intent"] for r in rows} - intents)
    script_mismatch = [r["text"] for r in rows
                       if (r["language"] == "tamil" and tamil_share(r["text"]) < 0.3)
                       or (r["language"] in ("english", "tanglish") and tamil_share(r["text"]) > 0.3)]

    train = [norm(r["text"]) for r in rows if r["split"] == "train"]
    held = [norm(r["text"]) for r in rows if r["split"] != "train"]
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5)).fit(train + held)
    sims = cosine_similarity(vec.transform(held), vec.transform(train)).max(axis=1)
    leakage = int((sims >= 0.95).sum())

    per_intent = Counter(r["intent"] for r in rows)
    return {
        "rows": len(rows),
        "missing_values": missing,
        "exact_duplicates_same_label": exact_dupes,
        "same_text_with_conflicting_labels": len(conflicting),
        "conflicting_examples": conflicting[:10],
        "unknown_intents": unknown_intents,
        "script_language_mismatches": len(script_mismatch),
        "script_mismatch_examples": script_mismatch[:10],
        "near_duplicate_leakage_eval_vs_train_(cos>=0.95)": leakage,
        "language_share_percent": {k: round(100 * v / len(rows), 1) for k, v in Counter(r["language"] for r in rows).items()},
        "split_counts": dict(Counter(r["split"] for r in rows)),
        "intents": len(per_intent),
        "smallest_intents": dict(sorted(per_intent.items(), key=lambda kv: kv[1])[:8]),
        "largest_intents": dict(sorted(per_intent.items(), key=lambda kv: -kv[1])[:5]),
    }


def _labels_by_text(rows):
    labels = {}
    for r in rows:
        labels.setdefault(norm(r["text"]), set()).add(r["intent"])
    return labels


def audit_knowledge():
    old = read_csv(DATASETS / "knowledge" / "agricultural_knowledge.csv")
    verified_path = ROOT / "data" / "verified" / "knowledge.jsonl"
    verified = [json.loads(l) for l in verified_path.read_text(encoding="utf-8").splitlines() if l.strip()] if verified_path.exists() else []
    return {
        "dataset_package_knowledge": {
            "records": len(old),
            "source_type": dict(Counter(r["source_type"] for r in old)),
            "with_source_url": 0,
            "verification_required_true": sum(1 for r in old if r["verification_required"].lower() == "true"),
            "verdict": "Generated text without source URLs — NOT served by the chatbot. Kept only as candidate topics.",
        },
        "official_source_knowledge": {
            "records": len(verified),
            "by_language": dict(Counter(r["language"] for r in verified)),
            "by_crop": dict(sorted(Counter(r["crop"] for r in verified).items())),
            "by_topic": dict(Counter(r["topic"] for r in verified)),
            "all_have_source_url": all(r.get("source_url") for r in verified),
            "verification_status": dict(Counter(r["verification_status"] for r in verified)),
        },
    }


def audit_misc():
    ood = read_csv(DATASETS / "nlp" / "out_of_domain_queries.csv")
    tanglish = json.loads((DATASETS / "tanglish" / "tanglish_dictionary.json").read_text(encoding="utf-8"))
    return {
        "out_of_domain_rows": len(ood),
        "out_of_domain_categories": dict(Counter(r["category"] for r in ood).most_common(12)),
        "tanglish_terms": tanglish.get("entry_count"),
        "image_manifest_rows": len(read_csv(DATASETS / "vision" / "image_dataset_manifest.csv")),
        "voice_metadata_rows_(no_audio)": len(read_csv(DATASETS / "voice" / "voice_queries.csv")),
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    report = {"farmer_queries": audit_queries(), "knowledge": audit_knowledge(), "other": audit_misc()}
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "dataset_audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    q, k = report["farmer_queries"], report["knowledge"]
    md = [
        "# Dataset audit", "",
        f"- farmer_queries: {q['rows']} rows, {q['intents']} intents, languages {q['language_share_percent']}",
        f"- missing values: {q['missing_values']}",
        f"- exact duplicates (same label): {q['exact_duplicates_same_label']}; same text with conflicting labels: {q['same_text_with_conflicting_labels']}",
        f"- unknown intent labels: {q['unknown_intents'] or 'none'}",
        f"- script/language mismatches: {q['script_language_mismatches']}",
        f"- eval rows nearly identical (cos ≥ 0.95) to a train row: {q['near_duplicate_leakage_eval_vs_train_(cos>=0.95)']}",
        f"- smallest intents: {q['smallest_intents']}", "",
        f"- dataset-package knowledge: {k['dataset_package_knowledge']['records']} records, source types {k['dataset_package_knowledge']['source_type']}, 0 with source URL → not served",
        f"- official-source knowledge (served): {k['official_source_knowledge']['records']} records, {k['official_source_knowledge']['by_language']}",
        f"- other: {report['other']}",
    ]
    (REPORTS / "dataset_audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
