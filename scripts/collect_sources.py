"""
Step 1 of the knowledge pipeline: collect pages from official agricultural sources.

    python scripts/collect_sources.py discover   # crawl allowed index pages → data/sources/candidates.json
    python scripts/collect_sources.py targeted   # crop-protection tree → data/sources/sources.json (+ fetches them)
    python scripts/collect_sources.py fetch      # download data/sources/sources.json → data/raw/

Rules this script enforces:
  * only hosts listed in ALLOWED_HOSTS (official / university sources)
  * robots.txt is checked for every URL (urllib.robotparser)
  * at least DELAY_SECONDS between requests, a descriptive User-Agent, local cache (never re-downloads)
  * every raw page is stored with its URL and retrieval time in data/raw/index.json
Raw pages are NEVER served directly: see clean_knowledge.py → validate_knowledge.py → import_supabase.py.
"""
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SOURCES = ROOT / "data" / "sources"
USER_AGENT = "FarmerAssist-knowledge-collector/1.0 (non-commercial farmer advisory research)"
DELAY_SECONDS = 2.0
ALLOWED_HOSTS = {"agritech.tnau.ac.in"}  # www.agritech.* links are rewritten to this host

# Crops FarmerAssist covers, with the words TNAU uses for them in URLs and link text (English + Tamil).
CROP_TERMS = {
    "paddy": ["rice", "paddy", "நெல்"],
    "tomato": ["tomato", "தக்காளி"],
    "chilli": ["chilli", "chillies", "மிளகாய்"],
    "banana": ["banana", "வாழை"],
    "coconut": ["coconut", "தென்னை"],
    "sugarcane": ["sugarcane", "sugar cane", "கரும்பு"],
    "groundnut": ["groundnut", "ground nut", "நிலக்கடலை"],
    "cotton": ["cotton", "பருத்தி"],
    "maize": ["maize", "corn", "மக்காச்சோளம்"],
    "brinjal": ["brinjal", "eggplant", "கத்தரி"],
    "onion": ["onion", "வெங்காயம்"],
    "drumstick": ["drumstick", "moringa", "முருங்கை"],
    "turmeric": ["turmeric", "மஞ்சள்"],
    "blackgram": ["blackgram", "black gram", "urd", "உளுந்து"],
    "greengram": ["greengram", "green gram", "mung", "பாசிப்பயறு", "பச்சைப்பயறு"],
}

_last_request = 0.0
_robots: dict[str, urllib.robotparser.RobotFileParser] = {}


def _robots_for(url: str) -> urllib.robotparser.RobotFileParser:
    parts = urllib.parse.urlsplit(url)
    base = f"{parts.scheme}://{parts.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser(f"{base}/robots.txt")
        try:
            rp.read()
        except Exception:  # unreadable robots.txt (TLS/network error): treat the host as off-limits
            rp.disallow_all = True
        _robots[base] = rp
    return _robots[base]


def allowed(url: str) -> bool:
    host = urllib.parse.urlsplit(url).hostname or ""
    return host in ALLOWED_HOSTS and _robots_for(url).can_fetch(USER_AGENT, urllib.parse.quote(url, safe=":/?&=%#~+,;@!$'()*[]"))


def cache_path(url: str) -> Path:
    return RAW / "pages" / (hashlib.sha256(url.encode()).hexdigest()[:20] + ".html")


def fetch(url: str) -> str | None:
    """Polite GET with cache. Returns HTML text, or None when disallowed / failed."""
    global _last_request
    path = cache_path(url)
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    if not allowed(url):
        print(f"  skip (not allowed): {url}")
        return None
    wait = DELAY_SECONDS - (time.time() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.time()
    # TNAU URLs often contain spaces ("crop_prot_crop diseases_..."): percent-encode for the request only.
    request_url = urllib.parse.quote(url, safe=":/?&=%#~+,;@!$'()*[]")
    request = urllib.request.Request(request_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 200:
                return None
            body = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
    except Exception as error:  # network / HTTP errors: record and move on
        print(f"  failed: {url} ({type(error).__name__})")
        return None
    text = body.decode(charset, errors="replace")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    index = load_index()
    index[url] = {"file": path.name, "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "bytes": len(body)}
    (RAW / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False), encoding="utf-8")
    return text


def load_index() -> dict:
    p = RAW / "index.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def links(url: str, html_text: str) -> list[tuple[str, str]]:
    """(absolute_url, link_text) pairs, same-site .html pages only."""
    out = []
    for href, label in re.findall(r'<a[^>]+href\s*=\s*"([^"#]+)"[^>]*>(.*?)</a>', html_text, re.I | re.S):
        absolute = urllib.parse.urljoin(url, href.strip()).replace("http://", "https://").replace("://www.agritech.", "://agritech.")
        if not re.search(r"\.html?$", absolute, re.I):
            continue
        text = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", label))).strip()
        out.append((absolute, text))
    return out


def crop_of(url: str, text: str) -> str | None:
    haystack = f"{urllib.parse.unquote(url)} {text}".lower()
    for crop, terms in CROP_TERMS.items():
        if any(term.lower() in haystack for term in terms):
            return crop
    return None


def discover() -> None:
    """Breadth-first over crop-protection / crop-production index pages (depth 3), recording crop pages."""
    seeds = [
        "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop_insect_pest.html",
        "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop_diseases.html",
        "https://agritech.tnau.ac.in/agriculture/agri_index.html",
        "https://agritech.tnau.ac.in/horticulture/horti_index.html",
        "https://agritech.tnau.ac.in/ta/crop_protection/crop_prot_crop_insect_pest_ta.html",
        "https://agritech.tnau.ac.in/ta/crop_protection/crop_prot_crop_diseases_ta.html",
    ]
    section = re.compile(r"/(ta/)?(crop_protection|agriculture|horticulture|Agriculture|ta)/", re.I)
    candidates: dict[str, dict] = {}
    frontier, seen = [(u, 0) for u in seeds], set()
    while frontier:
        url, depth = frontier.pop(0)
        if url in seen or depth > 3:
            continue
        seen.add(url)
        html_text = fetch(url)
        if not html_text:
            continue
        for link, text in links(url, html_text):
            if not section.search(link) or (urllib.parse.urlsplit(link).hostname or "") not in ALLOWED_HOSTS:
                continue
            crop = crop_of(link, text)
            if crop:
                candidates.setdefault(link, {"crop": crop, "link_text": text, "found_on": url,
                                             "language": "tamil" if "/ta/" in link or link.endswith("_ta.html") or "tamain" in link else "english"})
            # Only keep crawling index-like pages, not every leaf page.
            if re.search(r"index|_pest|diseases|insect|crop_prot|cropproduction|horti_|agri_", link, re.I) and link not in seen:
                frontier.append((link, depth + 1))
    SOURCES.mkdir(parents=True, exist_ok=True)
    out = SOURCES / "candidates.json"
    out.write_text(json.dumps(candidates, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(candidates)} crop pages found on {len(seen)} visited pages → {out.relative_to(ROOT)}")


PROTECTION_HUBS = [
    "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop_insect_agri_pest.html",
    "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop_insect_horti_pest.html",
    "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop_diseases_agri.html",
    "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop_diseases_horti.html",
    "https://agritech.tnau.ac.in/ta/crop_protection/crop_prot_crop_insect_pest_ta.html",
    "https://agritech.tnau.ac.in/ta/crop_protection/crop_prot_crop_diseases_ta.html",
]
_CATEGORY = re.compile(r"vegetable|fruit|spice|plant|pulse|cereal|oilseed|oil_|cash|agri|horti", re.I)
_HUB = re.compile(r"_index|index\.html|crop_prot\.html|crop_prot_ta\.html|_horti\.html|_agri\.html|_pest\.html|_pest_ta\.html|_diseases_ta\.html", re.I)


def topic_of(url: str) -> str:
    u = urllib.parse.unquote(url).lower()
    return "pest" if ("insect" in u or "pest" in u) else "disease" if "disease" in u else "protection"


def targeted() -> None:
    """hub → category → crop page → individual pest/disease pages. Writes data/sources/sources.json."""
    selected: dict[str, dict] = {}
    visited: set[str] = set()

    def walk(url: str, crop: str | None, depth: int) -> None:
        html_text = fetch(url)
        if not html_text:
            return
        for link, text in links(url, html_text):
            if "/crop_protection/" not in link or link in visited:
                continue
            visited.add(link)
            found = crop_of(link, text)
            if crop is None and found:  # a crop page
                selected[link] = {"url": link, "crop": found, "topic": topic_of(link), "level": "crop", "link_text": text}
                walk(link, found, depth + 1)
            elif crop is None and depth < 2 and _CATEGORY.search(urllib.parse.unquote(link)) and not _HUB.search(link):
                walk(link, None, depth + 1)  # a category page (vegetables, pulses, …)
            elif crop is not None and not _HUB.search(link) and (found in (None, crop)):
                # an individual pest/disease page under this crop — collected, not followed further
                selected.setdefault(link, {"url": link, "crop": crop, "topic": topic_of(link), "level": "leaf", "link_text": text})

    for hub in PROTECTION_HUBS:
        visited.add(hub)
        walk(hub, None, 0)

    # Second pass: every crop page contributes all of its same-crop leaf pages, even if a link was first
    # seen elsewhere during the walk (the shared `visited` set can hide them).
    # A page first recorded as a leaf can itself be a crop hub (the paddy pest index is linked from the
    # paddy disease page), so expand every selected page; leaves only contribute links naming the same crop.
    for item in list(selected.values()):
        html_text = fetch(item["url"])
        if not html_text:
            continue
        for link, text in links(item["url"], html_text):
            found = crop_of(link, text)
            allowed = found == item["crop"] if item["level"] == "leaf" else found in (None, item["crop"])
            if "/crop_protection/" in link and link not in selected and not _HUB.search(link) and allowed:
                selected[link] = {"url": link, "crop": item["crop"], "topic": topic_of(link) if topic_of(link) != "protection" else item["topic"],
                                  "level": "leaf", "link_text": text}

    for item in selected.values():
        u = item["url"]
        item["language"] = "tamil" if ("/ta/" in u or re.search(r"_ta(main)?\.html$|tamain", u)) else "english"
    SOURCES.mkdir(parents=True, exist_ok=True)
    out = SOURCES / "sources.json"
    out.write_text(json.dumps(sorted(selected.values(), key=lambda s: (s["crop"], s["topic"], s["url"])), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(selected)} crop-protection pages selected → {out.relative_to(ROOT)}")


def fetch_selected() -> None:
    """Downloads every URL listed in data/sources/sources.json (the reviewed selection)."""
    selected = json.loads((SOURCES / "sources.json").read_text(encoding="utf-8"))
    ok = 0
    for item in selected:
        if fetch(item["url"]):
            ok += 1
    print(f"{ok}/{len(selected)} pages available in data/raw/pages")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    {"discover": discover, "targeted": targeted, "fetch": fetch_selected}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
