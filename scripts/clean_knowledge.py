"""
Step 2 of the knowledge pipeline: raw official pages → structured records (data/processed/knowledge.jsonl).

    python scripts/clean_knowledge.py

Extraction is verbatim: headings and lines are kept as published, only site navigation/boilerplate is
removed. Nothing is paraphrased or generated. Every record carries its source URL and retrieval time.
Pages without real content (index/list pages) are skipped and counted in the report.
"""
import hashlib
import html
import json
import re
import sys
import urllib.parse
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from collect_sources import cache_path, load_index  # noqa: E402

SOURCES = ROOT / "data" / "sources" / "sources.json"
OUT = ROOT / "data" / "processed" / "knowledge.jsonl"
REPORT = ROOT / "data" / "processed" / "clean_report.json"
PUBLISHER = "TNAU Agritech Portal"
MAX_CONTENT = 2400

BOILERPLATE = re.compile(
    r"^(home\s*\|.*|©.*|copyright.*|.*all rights reserved.*|updated on.*|back|top|next|previous|print|"
    r"முகப்பு\s*\|.*|.*\|\s*contact( us)?$|click here.*|.*visitors?.*|tnau agritech portal ::.*)$",
    re.I,
)
SECTION = re.compile(
    r"^(symptoms?( of damage)?|damage symptoms?|identification( of the (pest|insect))?|management|control( measures)?|"
    r"pest management|disease management|favou?rable conditions?|mode of spread( and survival)?|pathogen|"
    r"causal organism|etiology|life cycle|biology|prevention|ipm|cultural methods?|chemical methods?|"
    r"biological control|mechanical methods?|nature of damage|host range|"
    r"அறிகுறி.*|சேதத்தின் அறிகுறி.*|கட்டுப்பாடு.*|மேலாண்மை.*|கட்டுப்படுத்தும் முறை.*|பூச்சியை.*கண்டறித.*|"
    r"நோய்க்காரணி.*|சாதகமான சூழ்நிலை.*|பரவுதல்.*)\s*[:：]?$",
    re.I,
)
CONTENT_SIGNAL = re.compile(r"symptom|management|control|damage|spray|identification|அறிகுறி|கட்டுப்|மேலாண்மை|தெளி", re.I)


def page_lines(raw: str) -> list[str]:
    text = re.sub(r"(?is)<(script|style|head|noscript).*?</\1>", " ", raw)
    text = re.sub(r"(?i)<br\s*/?>|</p>|</tr>|</li>|</h\d>|</div>|</td>|</table>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    lines = []
    for line in text.splitlines():
        line = re.sub(r"[ \t\xa0​]+", " ", line).strip(" -–•*·")
        if not line or len(line) <= 1 or BOILERPLATE.match(line):
            continue
        if line.count("|") >= 3:  # site navigation menu (English or Tamil)
            continue
        lines.append(line)
    return lines


def is_caption(line: str) -> bool:
    """Photo captions / tab labels ("Young larva", "இளம் புழு", "Other Management"): 1–2 words, no numbers."""
    return len(line.split()) <= 2 and not SECTION.match(line) and not re.search(r"[\d:：]", line)


def structure(lines: list[str]) -> tuple[str, str, str]:
    """(breadcrumb, heading, formatted content) — sections as **Heading:** followed by bullet lines."""
    breadcrumb = next((l for l in lines[:6] if "::" in l), "")
    body = [l for l in lines if l != breadcrumb and "::" not in l]
    heading = body[0].rstrip(":： ") if body else ""
    out: list[str] = []
    for line in body[1:]:
        if is_caption(line):
            continue
        # Known headings, or any short line ending with a colon ("தாக்குதலின் அறிகுறிகள் :")
        if SECTION.match(line) or (len(line.split()) <= 5 and re.search(r"[:：]\s*$", line)):
            out.append(f"\n**{line.rstrip(':： ')}:**")
        else:
            out.append(f"- {line}")
    content = "\n".join(out).strip()
    if len(content) > MAX_CONTENT:  # cut at a line boundary
        content = content[:MAX_CONTENT].rsplit("\n", 1)[0] + "\n- …(see source for the full page)"
    return breadcrumb, heading, content


def tamil_share(text: str) -> float:
    letters = re.findall(r"[a-zA-Z஀-௿]", text)
    return sum("஀" <= c <= "௿" for c in letters) / max(1, len(letters))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    index = load_index()
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    records, skipped = [], Counter()
    for source in sources:
        url = source["url"]
        path = cache_path(url)
        if not path.exists():
            skipped["not_downloaded"] += 1
            continue
        lines = page_lines(path.read_text(encoding="utf-8", errors="replace"))
        breadcrumb, heading, content = structure(lines)
        if len(content) < 120 or not CONTENT_SIGNAL.search(content) or content.count("\n- ") < 2:
            skipped["no_substantive_content"] += 1
            continue
        language = "tamil" if tamil_share(content) >= 0.3 else "english"
        name = re.sub(r"\s+", " ", heading)[:120]
        crop = source["crop"]
        title = f"{name} ({crop} {source['topic']})" if language == "english" else name
        records.append({
            "id": "tnau_" + hashlib.sha1(url.encode()).hexdigest()[:12],
            "crop": crop,
            "topic": source["topic"],
            "subtopic": re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:60] if language == "english" else None,
            "language": language,
            "title": title,
            "content": content,
            "breadcrumb": breadcrumb,
            "keywords": [crop, source["topic"], name.split(":")[0].strip()],
            "publisher": PUBLISHER,
            "source": f"{PUBLISHER} (agritech.tnau.ac.in), Tamil Nadu Agricultural University",
            "source_url": url,
            "retrieved_at": index.get(url, {}).get("retrieved_at"),
            "verification_status": "official_source_pending_review",
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    report = {
        "pages_in_selection": len(sources),
        "records_extracted": len(records),
        "skipped": dict(skipped),
        "by_crop": dict(Counter(r["crop"] for r in records)),
        "by_topic": dict(Counter(r["topic"] for r in records)),
        "by_language": dict(Counter(r["language"] for r in records)),
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
