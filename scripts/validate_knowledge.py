"""
Step 4 of the knowledge pipeline: validate records before they may be served.

    python scripts/validate_knowledge.py   (data/processed/knowledge_dedup.jsonl → data/verified/knowledge.jsonl)

A record is accepted only if every check passes; rejected records are listed with reasons in
data/verified/validation_report.json. Accepted records keep verification_status
"official_source_pending_review" until an agronomist reviews them (set "expert_verified" then).
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "processed" / "knowledge_dedup.jsonl"
OUT = ROOT / "data" / "verified" / "knowledge.jsonl"
REPORT = ROOT / "data" / "verified" / "validation_report.json"

REQUIRED = ["id", "crop", "topic", "language", "title", "content", "publisher", "source", "source_url", "retrieved_at", "verification_status"]
CROPS = {"paddy", "tomato", "chilli", "banana", "coconut", "sugarcane", "groundnut", "cotton", "maize", "brinjal", "onion",
         "drumstick", "turmeric", "blackgram", "greengram", "general"}
TOPICS = {"pest", "disease", "protection", "nutrient", "irrigation", "cultivation", "scheme"}
LANGUAGES = {"english", "tamil"}
ALLOWED_HOSTS = {"agritech.tnau.ac.in"}
STATUSES = {"official_source_pending_review", "expert_verified"}
JUNK = re.compile(r"page not found|404|under construction|javascript|cookie|lorem ipsum", re.I)


def tamil_share(text: str) -> float:
    letters = re.findall(r"[a-zA-Z஀-௿]", text)
    return sum("஀" <= c <= "௿" for c in letters) / max(1, len(letters))


def problems(r: dict) -> list[str]:
    found = [f"missing {k}" for k in REQUIRED if not r.get(k)]
    if r.get("crop") not in CROPS:
        found.append(f"unknown crop {r.get('crop')!r}")
    if r.get("topic") not in TOPICS:
        found.append(f"unknown topic {r.get('topic')!r}")
    if r.get("language") not in LANGUAGES:
        found.append(f"unsupported language {r.get('language')!r}")
    if (urlsplit(r.get("source_url", "")).hostname or "") not in ALLOWED_HOSTS:
        found.append("source is not an approved official host")
    if r.get("verification_status") not in STATUSES:
        found.append("invalid verification_status")
    content = r.get("content", "")
    if len(content) < 120:
        found.append("content too short")
    if JUNK.search(content):
        found.append("content looks like an error/boilerplate page")
    share = tamil_share(content)
    if r.get("language") == "tamil" and share < 0.3:
        found.append("labelled Tamil but mostly Latin script")
    if r.get("language") == "english" and share > 0.2:
        found.append("labelled English but contains mostly Tamil script")
    return found


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    records = [json.loads(l) for l in IN.read_text(encoding="utf-8").splitlines() if l.strip()]
    accepted, rejected = [], []
    for r in records:
        issues = problems(r)
        (rejected if issues else accepted).append({"id": r.get("id"), "url": r.get("source_url"), "problems": issues} if issues else r)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in accepted:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    report = {
        "input": len(records),
        "accepted": len(accepted),
        "rejected": len(rejected),
        "rejection_reasons": dict(Counter(p for r in rejected for p in r["problems"])),
        "accepted_by_crop": dict(sorted(Counter(r["crop"] for r in accepted).items())),
        "accepted_by_topic": dict(Counter(r["topic"] for r in accepted)),
        "accepted_by_language": dict(Counter(r["language"] for r in accepted)),
        "tamil_with_english_pair": sum(1 for r in accepted if r["language"] == "tamil" and r.get("pair_id")),
        "rejected_records": rejected,
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "rejected_records"}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
