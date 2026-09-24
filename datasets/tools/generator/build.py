# -*- coding: utf-8 -*-
"""Builds the FarmerAssist dataset package. Deterministic (seed 7)."""
import csv, json, os, random, re, shutil
from collections import Counter, defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import kb, intents_seed as S, lexicon as L

random.seed(7)
OUT = "FarmerAssist_Datasets"
TODAY = "2026-09-23"
TA_RE = re.compile(r"[\u0B80-\u0BFF]")
LAT_RE = re.compile(r"[A-Za-z]")

# ------------------------------------------------------------------ crop names
EN_NAMES = {"paddy": ["paddy", "rice"], "onion": ["onion", "small onion"], "drumstick": ["drumstick", "moringa"],
            "blackgram": ["black gram", "urad"], "greengram": ["green gram", "moong"]}
def crop_name(c, lang):
    if lang == "en":
        return random.choice(EN_NAMES.get(c, [kb.CROPS[c][0].lower()]))
    if lang == "ta":
        return kb.CROPS[c][1]
    return random.choice(kb.CROPS[c][2])

# ------------------------------------------------------------------ lexicon lookups
LEXE = L.parse_lex()
def auto_variants(term):
    v = {term}
    rules = [("th", "t"), ("dh", "d"), ("zh", "l"), ("aa", "a"), ("ee", "i"), ("oo", "u"), ("kk", "k"), ("pp", "p")]
    for a, b in rules:
        if a in term:
            v.add(term.replace(a, b))
    if term.endswith("u") and len(term) > 3:
        v.add(term[:-1])
    return sorted(v)

NONDOMAIN = {"function", "address", "number", "time", "unit"}
DOMAIN_LAT, DOMAIN_TA = set(), set()
EN_DOMAIN = set("disease sick pest pests insects insect yellow yellowing spots spot leaves leaf fertilizer urea manure water rain flood price rate seed seeds variety soil harvest curl curling rot rotting wilt wilting borer worms worm dead heart drip sprinkler subsidy insurance scheme kisan tractor machine photo drought heat blight roots root fruits fruit whitefly aphids thrips mites bollworm nitrogen phosphorus potassium zinc iron organic compost vermicompost storage store dry sow sowing plant planting season market sell irrigate irrigation weather forecast spray tiller harvester transplanter purple brown black white burnt drying scorched".split())
def is_domain(tok):
    t = re.sub(r"[?!.,]", "", tok.lower())
    if TA_RE.search(t):
        return any(t.startswith(k) and len(k) / len(t) >= 0.55 for k in DOMAIN_TA if len(k) >= 2)
    return t in DOMAIN_LAT or t in EN_DOMAIN
VARMAP = {}      # term -> variants (for phonetic noise)
LOOKUP = {}      # any latin form -> english
TA_LOOKUP = {}   # tamil form -> english
for e in LEXE:
    variants = sorted(set(auto_variants(e["term"]) + e["extra"] + [e["term"]]))
    e["variations"] = variants
    VARMAP[e["term"]] = [v for v in variants if v != e["term"]]
    eng = re.sub(r"\s*\(.*?\)", "", e["english"][0]).strip()
    for v in variants:
        LOOKUP.setdefault(v.lower(), eng)
        if e["category"] not in NONDOMAIN: DOMAIN_LAT.add(v.lower())
    TA_LOOKUP.setdefault(e["tamil"], eng)
    if e["category"] not in NONDOMAIN: DOMAIN_TA.add(e["tamil"])
TA_INFLECT = {"நெல்லு": "paddy", "நெல்லில்": "paddy", "நெல்லுக்கு": "paddy", "இலைகள்": "leaves", "இலையில்": "leaf",
              "இலையில": "leaf", "பூச்சிகள்": "pests", "பூச்சிய": "pest", "உரத்த": "fertilizer", "உரத்தை": "fertilizer",
              "தண்ணி": "water", "மண்ணுல": "soil", "வயல்ல": "field", "வயலில்": "field", "மஞ்சளா": "yellow",
              "மஞ்சளாகுது": "turning yellow", "வாடுது": "wilting", "அழுகுது": "rotting", "கருகுது": "scorching",
              "காயுது": "drying", "சுருண்டு": "curled", "புழு": "worm", "காயில": "in fruit", "காய்க்குள்ள": "inside fruit",
              "மழைக்கு": "rain", "மழையால": "due to rain", "விதைக்கணும்": "sow", "அறுவடை": "harvest", "விலை": "price"}
TA_LOOKUP.update(TA_INFLECT)
for _c, _v in kb.CROPS.items(): TA_LOOKUP[_v[1]] = _v[0].split(" (")[0].lower(); DOMAIN_TA.add(_v[1])
TA_KEYS = sorted(TA_LOOKUP, key=len, reverse=True)

def normalize(text):
    t = re.sub(r"[?!.,;:\"'()]", " ", text.lower())
    toks = t.split()
    has_leaf = any(x in toks for x in ("ilai", "elai", "leaf", "leaves", "இலை", "இலையில")) or "இலை" in t
    out, i = [], 0
    while i < len(toks):
        tok = toks[i]
        two = " ".join(toks[i:i + 2])
        if two in LOOKUP and " " in two:
            out.append(LOOKUP[two]); i += 2; continue
        if tok in ("manjal", "manjala", "மஞ்சள்", "மஞ்சளா"):
            out.append("yellow" if has_leaf else "turmeric"); i += 1; continue
        if TA_RE.search(tok):
            hit = TA_LOOKUP.get(tok)
            if not hit:
                for k in TA_KEYS:
                    if len(k) >= 2 and tok.startswith(k) and len(k) / len(tok) >= 0.55:
                        hit = TA_LOOKUP[k]; break
            out.append(hit or tok)
        elif tok in LOOKUP and not re.fullmatch(r"[a-z]+", tok) is None and tok not in ENGLISH_KEEP:
            out.append(LOOKUP[tok])
        else:
            out.append(tok)
        i += 1
    return " ".join(out)
ENGLISH_KEEP = {"spray", "drip", "seed", "rate", "loan", "problem", "attack", "hybrid", "variety", "yield",
                "insurance", "subsidy", "fertilizer", "medicine", "tractor", "motor", "current", "sir", "acre",
                "kilo", "litre", "cent", "hectare", "power", "tiller", "rotavator", "en", "adi", "pen", "ee", "man",
                "pal", "mean", "lemon", "tea", "coffee", "ragi", "bore", "godown", "store", "market", "organic",
                "farmer", "apply", "register", "certificate", "government", "govt", "scheme", "help", "reason",
                "brown", "harvester", "transplanter", "machine", "rent", "weather", "monsoon", "mulching", "maa"}

# ------------------------------------------------------------------ noise
STOP = {
 "en": set("the a an is my are in of to for how what should i do does can which when why with on it this after before and be me there much per get from by at its some".split()),
 "tl": set("enna epdi eppo iruku la ku ah pannanum sollunga sir anna oru ellam romba nu um yen naala apram ku podanum kulla mela vachu".split()),
 "ta": {"என்ன", "எப்படி", "இருக்கு", "ஏன்", "பண்றது", "செய்யணும்", "சொல்லுங்க", "எப்போ", "ஒரு", "எல்லாம்", "இந்த", "போகுது"},
}
EN_HOMO = {"paddy": "party", "rice": "rise", "urea": "uria", "pest": "past", "pests": "pasts", "leaves": "leafs",
           "fertilizer": "fertiliser", "borer": "border", "whitefly": "white fly", "yellow": "yello", "brinjal": "brinjol",
           "drip": "trip", "wilting": "wilding", "insects": "insex", "harvest": "harvist", "seeds": "seats"}
EN2TL = {"leaves": "ilai", "leaf": "ilai", "pest": "poochi", "pests": "poochi", "insects": "poochi", "fertilizer": "uram",
         "water": "thanni", "disease": "noi", "worms": "puzhu", "worm": "puzhu", "rain": "mazhai", "price": "vilai",
         "seeds": "vidhai", "soil": "mann", "field": "vayal", "plants": "sedi", "plant": "sedi"}
TL2EN = {"ilai": "leaf", "poochi": "pest", "uram": "fertilizer", "thanni": "water", "noi": "disease", "puzhu": "worm",
         "mazhai": "rain", "vilai": "price", "vidhai": "seed", "mann": "soil", "vayal": "field", "sedi": "plant",
         "marundhu": "medicine", "aruvadai": "harvest", "kaai": "fruit"}
TA_SWAPS = [("ழ", "ள"), ("ண", "ன"), ("ற", "ர"), ("ந", "ன"), ("ல", "ள")]
SLANG = {"en": (["sir ", "bro ", "pls tell ", "anna "], [" pls", " sir urgent", " what to do sir", " help"]),
         "ta": (["ஐயா ", "அண்ணா ", "சார் "], [" என்ன பண்றது", " சொல்லுங்க", " உடனே சொல்லுங்க"]),
         "tl": (["sir ", "anna ", "ayya ", "bro "], [" enna pannanum", " sollunga pls", " urgent sir", " help pannunga"])}

def typo(word):
    if len(word) < 4: return word
    i = random.randrange(1, len(word) - 1)
    op = random.choice(["del", "dup", "swap", "vowel"])
    if op == "del": return word[:i] + word[i + 1:]
    if op == "dup": return word[:i] + word[i] + word[i:]
    if op == "swap": return word[:i] + word[i + 1] + word[i] + word[i + 2:]
    if word[i] in "aeiou": return word[:i] + random.choice([v for v in "aeiou" if v != word[i]]) + word[i + 1:]
    return word[:i] + word[i + 1:]

def apply_noise(text, lang, kind, crop=None, crop_local=None):
    """Returns (noisy_text, language_override) or (None, None) if not applicable."""
    toks = text.split()
    if kind == "spelling_error":
        if lang == "ta":
            idx = [m.start() for m in re.finditer("்", text)]
            if idx and random.random() < 0.5:
                i = random.choice(idx); return text[:i] + text[i + 1:], None
            for a, b in random.sample(TA_SWAPS, len(TA_SWAPS)):
                if a in text: return text.replace(a, b, 1), None
            return None, None
        cand = [i for i, w in enumerate(toks) if len(w) >= 4]
        if not cand: return None, None
        i = random.choice(cand); toks[i] = typo(toks[i]); return " ".join(toks), None
    if kind == "phonetic" and lang == "tl":
        cand = [i for i, w in enumerate(toks) if VARMAP.get(w.lower())]
        if not cand: return None, None
        i = random.choice(cand); toks[i] = random.choice(VARMAP[toks[i].lower()]); return " ".join(toks), None
    if kind == "short_query":
        ws = re.sub(r"[?,.!]", "", text).split()
        keep = [w for w in ws if (crop_local and w in crop_local.split()) or is_domain(w)][:3]
        if len(keep) < 2 or len(keep) >= len(ws): return None, None
        return (" ".join(keep).lower() if lang != "ta" else " ".join(keep)), None
    if kind == "missing_words":
        cand = [i for i, w in enumerate(toks) if not is_domain(w) and not (crop_local and w in crop_local.split())]
        if len(toks) < 4 or not cand: return None, None
        del toks[random.choice(cand)]; return " ".join(toks), None
    if kind == "farmer_slang":
        pre, suf = SLANG[lang]
        return (random.choice(pre) + text if random.random() < 0.5 else text.rstrip("?") + random.choice(suf)), None
    if kind == "mixed_language":
        if lang == "ta":
            if crop and crop_local and crop_local in text:
                return text.replace(crop_local, kb.CROPS[crop][0].split(" (")[0].lower(), 1), "mixed"
            return text.rstrip("?") + random.choice([" problem", " spray பண்ணலாமா", " solution சொல்லுங்க"]), "mixed"
        table = EN2TL if lang == "en" else TL2EN
        cand = [i for i, w in enumerate(toks) if w.lower() in table]
        if not cand: return None, None
        i = random.choice(cand); toks[i] = table[toks[i].lower()]; return " ".join(toks), "mixed"
    if kind == "voice_transcription_error":
        t = re.sub(r"[?!.,]", "", text)
        if lang == "en":
            t = t.lower(); hits = [w for w in t.split() if w in EN_HOMO]
            if hits: w = random.choice(hits); t = re.sub(rf"\b{w}\b", EN_HOMO[w], t, count=1)
            return t, None
        if lang == "ta":
            for a, b in random.sample(TA_SWAPS, 2):
                t = t.replace(a, b, 1)
            ws = t.split()
            if len(ws) > 2 and random.random() < 0.5:
                i = random.randrange(len(ws) - 1); ws[i:i + 2] = [ws[i] + ws[i + 1]]
            return " ".join(ws), None
        t = t.lower().replace("zh", "l").replace("dh", "d")
        ws = t.split()
        if len(ws) > 2:
            i = random.randrange(len(ws) - 1); ws[i:i + 2] = [ws[i] + ws[i + 1]]
        return " ".join(ws), None
    return None, None

NOISE_BY_LANG = {"en": ["spelling_error", "short_query", "missing_words", "farmer_slang", "mixed_language", "voice_transcription_error"],
                 "ta": ["spelling_error", "short_query", "missing_words", "farmer_slang", "mixed_language", "voice_transcription_error"],
                 "tl": ["spelling_error", "phonetic", "phonetic", "short_query", "missing_words", "farmer_slang", "mixed_language", "voice_transcription_error"]}
LANG_LABEL = {"en": "english", "ta": "tamil", "tl": "tanglish"}
def script_of(t):
    ta, la = bool(TA_RE.search(t)), bool(LAT_RE.search(t))
    return "mixed" if ta and la else "tamil" if ta else "latin"
def difficulty(noise):
    if noise == "none": return "easy"
    if noise in ("farmer_slang", "missing_words", "phonetic", "spelling_error"): return "medium"
    return "hard"

TOPIC = {"crop_disease": "disease", "pest": "pest", "fertilizer": "nutrition", "soil": "soil", "irrigation": "water",
         "seed": "seed", "crop_info": "crop_management", "weather": "weather", "market": "market", "scheme": "scheme",
         "machinery": "machinery", "image_request": "image", "greeting": "conversation", "thanks": "conversation",
         "agriculture_question": "general", "out_of_domain": "out_of_domain"}
KB_TOPIC = {"sowing_time": "season", "harvesting": "harvest", "post_harvest_storage": "post_harvest", "irrigation": "irrigation",
            "drip_irrigation": "irrigation", "water_shortage": "irrigation", "fertilizer": "fertilizer",
            "fertilizer_timing": "fertilizer", "organic_fertilizer": "fertilizer", "seed_selection": "seed",
            "seed_treatment": "seed", "crop_disease": "common_problems", "pest_attack": "common_problems",
            "yellow_leaf": "common_problems", "leaf_spot": "common_problems", "wilting": "common_problems"}
DEF_KB = {"nitrogen_deficiency": "KB_DEF_N", "phosphorus_deficiency": "KB_DEF_P",
          "potassium_deficiency": "KB_DEF_K", "micronutrient_deficiency": "KB_DEF_Zn"}
KB_LOCAL = {"season", "duration", "common_problems"}   # topics that also exist in ta/tanglish

def response_id(intent, rtype, crop, lang):
    if intent in DEF_KB: return f"{DEF_KB[intent]}_{'en' if lang == 'en' else 'ta' if lang == 'ta' else 'tanglish'}"
    t = KB_TOPIC.get(intent)
    if t and crop:
        lg = "en" if lang == "en" or t not in KB_LOCAL else ("ta" if lang == "ta" else "tanglish")
        return f"KB_{crop}_{t}_{lg}"
    return f"TPL_{rtype}"

# ------------------------------------------------------------------ build farmer_queries
rows, seen = [], set()
def norm_key(t): return re.sub(r"\s+", " ", re.sub(r"[?!.,]", "", t.lower())).strip()
def add(text, lang, intent, crop, noise, rtype, group, lang_override=None):
    k = norm_key(text)
    if not k or k in seen: return False
    seen.add(k)
    language = lang_override or LANG_LABEL[lang]
    rows.append(dict(text=text, language=language, script=script_of(text), intent=intent, crop=crop or "",
                     topic=TOPIC[rtype], normalized_text=normalize(text), difficulty=difficulty(noise), noise_type=noise,
                     expected_response_type=rtype, response_id=response_id(intent, rtype, crop, lang), group_id=group))
    return True

for intent, spec in S.INTENTS.items():
    for lang in ("en", "ta", "tl"):
        for si, seed in enumerate(spec[lang]):
            group = f"{intent}__{lang}__{si}"
            fills = [(None, seed)]
            if "{c}" in seed and spec["crops"]:
                chosen = random.sample(spec["crops"], min(3, len(spec["crops"])))
                fills = []
                for c in chosen:
                    local = crop_name(c, lang)
                    fills.append((c, seed.replace("{c}", local), local))
                fills = [(c, t, l) for c, t, l in fills]
            else:
                fills = [(None, seed.replace("{c}", ""), None)]
            n_noise = (1 if len(fills) > 1 else 2) + (1 if lang == "ta" else 0)
            for c, clean, local in fills:
                clean = re.sub(r"\s+", " ", clean).strip()
                add(clean, lang, intent, c, "none", spec["response_type"], group)
                kinds = random.sample(NOISE_BY_LANG[lang], len(NOISE_BY_LANG[lang]))
                made = 0
                for kind in kinds:
                    if made >= n_noise: break
                    if kind == "short_query" and intent in ("greeting", "thanks", "image_upload_help", "agri_general_info"): continue
                    noisy, lo = apply_noise(clean, lang, kind, c, local)
                    if noisy and add(noisy, lang, intent, c, kind, spec["response_type"], group, lo):
                        made += 1

# out-of-domain rows
ood_rows = []
for cat, (en, ta, tl) in L.OOD.items():
    for lang, block in (("en", en), ("ta", ta), ("tl", tl)):
        for i, t in enumerate(block.split("|")):
            t = t.strip()
            ood_rows.append((t, lang, cat))
            group = f"ood__{cat}__{lang}__{i}"
            add(t, lang, "out_of_domain", None, "none", "out_of_domain", group)
            if random.random() < 0.35:
                kind = random.choice(["spelling_error", "voice_transcription_error", "farmer_slang"])
                noisy, lo = apply_noise(t, lang, kind)
                if noisy: add(noisy, lang, "out_of_domain", None, kind, "out_of_domain", group, lo)

# ------------------------------------------------------------------ group-aware split
def split_groups(rows):
    by_int = defaultdict(list)
    for g in sorted({(r["intent"], r["group_id"]) for r in rows}):
        by_int[g[0]].append(g[1])
    assign = {}
    for intent, groups in by_int.items():
        random.shuffle(groups)
        n = len(groups); nt = max(1, round(n * 0.15)); nv = max(1, round(n * 0.15))
        for i, g in enumerate(groups):
            assign[g] = "test" if i < nt else "validation" if i < nt + nv else "train"
    return assign
ASSIGN = split_groups(rows)
for r in rows: r["split"] = ASSIGN[r["group_id"]]

# leakage check (char n-gram TF-IDF on normalized text), then move leaking groups to train
def leakage(rows, thr=0.90):
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1)
    X = vec.fit_transform([r["normalized_text"] for r in rows])
    tr = [i for i, r in enumerate(rows) if r["split"] == "train"]
    ev = [i for i, r in enumerate(rows) if r["split"] != "train"]
    sims = (X[ev] @ X[tr].T).toarray()
    out = []
    for a, i in enumerate(ev):
        j = tr[int(np.argmax(sims[a]))]
        if sims[a].max() >= thr and rows[i]["group_id"] != rows[j]["group_id"]:
            out.append((i, j, float(sims[a].max())))
    return out
leak_before = leakage(rows)
leak_before_txt_pairs = [(rows[i]["text"], rows[j]["text"], s) for i, j, s in leak_before]
for i, j, s in leak_before:
    ASSIGN[rows[i]["group_id"]] = "train"
for r in rows: r["split"] = ASSIGN[r["group_id"]]
leak_after = leakage(rows)

# ids
random.shuffle(rows)
rows.sort(key=lambda r: {"train": 0, "validation": 1, "test": 2}[r["split"]])
for n, r in enumerate(rows, 1): r["id"] = f"FQ{n:05d}"

# ------------------------------------------------------------------ writers
def wcsv(path, rows, cols):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in rows: w.writerow({c: r.get(c, "") for c in cols})
def wjson(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, indent=2)

shutil.rmtree(OUT, ignore_errors=True)
FQ_COLS = ["id", "text", "language", "script", "intent", "crop", "topic", "normalized_text", "difficulty",
           "noise_type", "expected_response_type", "response_id", "group_id", "split"]
wcsv(f"{OUT}/nlp/farmer_queries.csv", rows, FQ_COLS)
with open(f"{OUT}/nlp/farmer_queries.jsonl", "w", encoding="utf-8") as f:
    for r in rows: f.write(json.dumps({c: r[c] for c in FQ_COLS}, ensure_ascii=False) + "\n")

# intents.json + intent_examples.csv
intents_json, ie = [], []
for intent, spec in S.INTENTS.items():
    ex = {}
    for lang in ("en", "ta", "tl"):
        ex[LANG_LABEL[lang]] = [s.replace("{c}", crop_name(spec["crops"][0], lang) if spec["crops"] else "").strip()
                                for s in spec[lang][:3]]
    negs = [{"text": t.replace("{c}", crop_name(spec["crops"][0], "en") if spec["crops"] else "crop"), "true_intent": ti}
            for t, ti in spec["negatives"]]
    intents_json.append(dict(intent_name=intent, description=spec["description"], response_type=spec["response_type"],
                             examples=ex, related_crops=spec["crops"], keywords=spec["keywords"], negative_examples=negs))
    for lang in ("en", "ta", "tl"):
        for si, seed in enumerate(spec[lang]):
            g = f"{intent}__{lang}__{si}"
            crops = random.sample(spec["crops"], min(3, len(spec["crops"]))) if "{c}" in seed and spec["crops"] else [None]
            for c in crops:
                t = re.sub(r"\s+", " ", seed.replace("{c}", crop_name(c, lang) if c else "")).strip()
                ie.append(dict(intent=intent, text=t, language=LANG_LABEL[lang], label="positive", true_intent=intent,
                               confused_with="", crop=c or "", split=ASSIGN.get(g, "train")))
    for t, ti in spec["negatives"]:
        for c in (random.sample(spec["crops"], min(2, len(spec["crops"]))) if spec["crops"] else [None]):
            ie.append(dict(intent=intent, text=t.replace("{c}", crop_name(c, "en") if c else "crop"), language="english",
                           label="negative", true_intent=ti, confused_with=ti, crop=c or "", split="train"))
intents_json.append(dict(intent_name="out_of_domain", description="Anything not about agriculture/farming",
                         response_type="out_of_domain", examples={"english": ["what is today's cricket score"],
                         "tamil": ["இந்தியாவின் பிரதமர் யார்"], "tanglish": ["oru joke sollu"]},
                         related_crops=[], keywords=[], negative_examples=[{"text": "today paddy price", "true_intent": "market_price"}]))
for t, lang, cat in ood_rows:
    g = [r for r in rows if r["text"] == t]
    ie.append(dict(intent="ANY_AGRICULTURE", text=t, language=LANG_LABEL[lang], label="negative", true_intent="out_of_domain",
                   confused_with="out_of_domain", crop="", split=g[0]["split"] if g else "train"))
seen_ie, ie2 = set(), []
for r in ie:
    k = (r["intent"], r["label"], norm_key(r["text"]))
    if k not in seen_ie: seen_ie.add(k); ie2.append(r)
for n, r in enumerate(ie2, 1): r["example_id"] = f"IE{n:05d}"
wjson(f"{OUT}/nlp/intents.json", intents_json)
wcsv(f"{OUT}/nlp/intent_examples.csv", ie2, ["example_id", "intent", "text", "language", "label", "true_intent", "confused_with", "crop", "split"])

# spelling variations
sv, sv_seen = [], set()
clean_rows = [r for r in rows if r["noise_type"] == "none" and r["intent"] != "out_of_domain"]
kinds_by = {"english": ["spelling_error", "voice_transcription_error"], "tamil": ["spelling_error", "voice_transcription_error"],
            "tanglish": ["spelling_error", "phonetic", "voice_transcription_error"]}
code = {"english": "en", "tamil": "ta", "tanglish": "tl"}
for r in clean_rows:
    for kind in kinds_by.get(r["language"], []):
        noisy, _ = apply_noise(r["text"], code[r["language"]], kind)
        if noisy and norm_key(noisy) != norm_key(r["text"]) and (r["text"], noisy) not in sv_seen:
            sv_seen.add((r["text"], noisy))
            sv.append(dict(original_text=r["text"], noisy_text=noisy, language=r["language"], error_type=kind,
                           intent=r["intent"], split=r["split"]))
for e in LEXE:   # word-level spelling variants from the dictionary
    for v in e["variations"]:
        if v != e["term"] and (e["term"], v) not in sv_seen:
            sv_seen.add((e["term"], v))
            sv.append(dict(original_text=e["term"], noisy_text=v, language="tanglish", error_type="word_variant", intent="", split=""))
wcsv(f"{OUT}/nlp/spelling_variations.csv", sv, ["original_text", "noisy_text", "language", "error_type", "intent", "split"])

# out of domain
ood_out = []
for n, (t, lang, cat) in enumerate(ood_rows, 1):
    lg = LANG_LABEL[lang]
    ood_out.append(dict(id=f"OOD{n:04d}", text=t, language=lg, category=cat, expected_intent="out_of_domain",
                        expected_response=L.OOD_RESPONSE[lg],
                        note="Allied sector (livestock/fisheries) — out of scope in v1; revisit later" if cat == "borderline_allied" else ""))
wcsv(f"{OUT}/nlp/out_of_domain_queries.csv", ood_out, ["id", "text", "language", "category", "expected_intent", "expected_response", "note"])

# weather queries
wq = [dict(id=r["id"], text=r["text"], language=r["language"], intent=r["intent"], crop=r["crop"],
           advisory_response_id="TPL_weather", split=r["split"]) for r in rows if r["intent"] in ("weather", "rain_damage", "drought", "heat_stress")]
wcsv(f"{OUT}/nlp/weather_queries.csv", wq, ["id", "text", "language", "intent", "crop", "advisory_response_id", "split"])

# normalization + dictionary
tn = {k: TA_LOOKUP[k] for k in sorted(TA_LOOKUP)}
wjson(f"{OUT}/nlp/tamil_normalization.json", {"_note": "For NLP processing only. Never replace the user's original message in the UI.", "map": tn})
dict_entries = [dict(term=e["term"], tamil=e["tamil"], variations=e["variations"], english=e["english"], category=e["category"]) for e in LEXE]
wjson(f"{OUT}/tanglish/tanglish_dictionary.json", {"_note": "manjal is ambiguous (turmeric vs yellow); resolve with context such as ilai/leaf.",
                                                    "entry_count": len(dict_entries), "entries": dict_entries,
                                                    "lookup": {k: LOOKUP[k] for k in sorted(LOOKUP)}})

# ------------------------------------------------------------------ knowledge base
K = []
def krec(kid, crop, topic, sub, lang, title, content, symptoms="", causes="", prevention="", management="", keywords="", st="curated_general_agronomy"):
    K.append(dict(knowledge_id=kid, crop=crop, topic=topic, subtopic=sub, language=lang, title=title, content=content,
                  symptoms=symptoms, causes=causes, prevention=prevention, management=management, keywords=keywords,
                  source_type=st, verification_required="true"))
dis_by_crop, pest_by_crop = defaultdict(list), defaultdict(list)
for d in kb.DISEASES:
    for c in d[1].split(";"): dis_by_crop[c].append(d)
for p in kb.PESTS:
    for c in p[1].split(";"): pest_by_crop[c].append(p)
for c, (en, ta, tls, sci, typ, typ_ta) in kb.CROPS.items():
    s_en, s_ta, s_tl = kb.SEASON[c]; d_en, d_ta, d_tl = kb.DURATION[c]
    kw = ";".join([en.lower(), ta] + tls)
    krec(f"KB_{c}_overview_en", c, "crop_information", "overview", "english", f"{en} overview",
         f"{en} ({sci}) is a {typ} crop grown in Tamil Nadu. {s_en} Duration: {d_en}.", keywords=kw)
    krec(f"KB_{c}_season_en", c, "planting", "season", "english", f"{en} sowing/planting season", s_en, keywords=kw)
    krec(f"KB_{c}_duration_en", c, "growth", "duration", "english", f"{en} crop duration", f"{en} takes {d_en}.", keywords=kw)
    krec(f"KB_{c}_soil_en", c, "soil", "suitable_soil", "english", f"Soil for {en}", kb.SOIL[c], keywords=kw)
    krec(f"KB_{c}_irrigation_en", c, "irrigation", "critical_stages", "english", f"Irrigation for {en}", kb.WATER[c], keywords=kw)
    krec(f"KB_{c}_fertilizer_en", c, "fertilizer", "general", "english", f"Fertilizer guidance for {en}",
         "Base fertilizer on a soil test (Soil Health Card). Apply well-decomposed organic manure before planting and split nitrogen into 2–3 doses. "
         + kb.FERT_NOTE.get(c, "") + " Exact quantities must come from TNAU recommendations via your agriculture office.", keywords=kw)
    krec(f"KB_{c}_seed_en", c, "seed", "selection_and_treatment", "english", f"Seed for {en}",
         f"Use certified seed or healthy planting material of a TNAU-recommended {en.lower()} variety suited to your district and season. "
         "Seed treatment with bio-agents (Trichoderma, Pseudomonas) and biofertilizers is commonly advised; get the method from the agriculture office.", keywords=kw)
    krec(f"KB_{c}_harvest_en", c, "harvesting", "maturity_signs", "english", f"Harvesting {en}", kb.HARVEST[c], keywords=kw)
    krec(f"KB_{c}_post_harvest_en", c, "post_harvest", "drying_storage", "english", f"Post-harvest handling of {en}", kb.POSTHARVEST[c], keywords=kw)
    dl, pl = dis_by_crop[c], pest_by_crop[c]
    krec(f"KB_{c}_common_problems_en", c, "common_problems", "diseases_and_pests", "english", f"Common problems in {en}",
         f"Diseases: {', '.join(d[2] for d in dl) or 'none listed'}. Pests: {', '.join(p[2] for p in pl) or 'none listed'}. "
         "Confirm diagnosis with the agriculture officer or KVK before treating.", keywords=kw)
    krec(f"KB_{c}_season_ta", c, "planting", "season", "tamil", f"{ta} பருவம்", s_ta, keywords=kw)
    krec(f"KB_{c}_duration_ta", c, "growth", "duration", "tamil", f"{ta} பயிர் காலம்", f"{ta}: {d_ta}.", keywords=kw)
    krec(f"KB_{c}_common_problems_ta", c, "common_problems", "diseases_and_pests", "tamil", f"{ta} பொதுவான பிரச்சனைகள்",
         f"நோய்கள்: {', '.join(d[3] for d in dl) or '—'}. பூச்சிகள்: {', '.join(p[3] for p in pl) or '—'}. சிகிச்சைக்கு முன் வேளாண் அலுவலர் அல்லது KVK-இல் உறுதி செய்யுங்கள்.", keywords=kw)
    krec(f"KB_{c}_season_tanglish", c, "planting", "season", "tanglish", f"{tls[0]} season", s_tl, keywords=kw)
    krec(f"KB_{c}_duration_tanglish", c, "growth", "duration", "tanglish", f"{tls[0]} duration", f"{tls[0]}: {d_tl}.", keywords=kw)
    krec(f"KB_{c}_common_problems_tanglish", c, "common_problems", "diseases_and_pests", "tanglish", f"{tls[0]} common problems",
         f"Noigal: {', '.join(d[2] for d in dl) or '—'}. Poochigal: {', '.join(p[2] for p in pl) or '—'}. Treat panna munnadi agri officer illa KVK la confirm pannunga.", keywords=kw)
for d in kb.DISEASES:
    prev, mgmt = kb.PATHOGEN_MGMT[d[4]]
    krec(f"KB_DIS_{d[0]}", d[1], "disease", d[4], "english", f"{d[2]} ({d[1].replace(';', ', ')})",
         f"{d[2]} is a {d[4]} disease caused by {d[5]}.", symptoms=d[6], causes=f"{d[5]}; favoured by {d[7]}",
         prevention=prev, management=mgmt, keywords=f"{d[2]};{d[3]}")
for p in kb.PESTS:
    krec(f"KB_PEST_{p[0]}", p[1], "pest", p[5], "english", f"{p[2]} ({p[1].replace(';', ', ')})",
         f"{p[2]} ({p[4]}) is a {p[5]} pest.", symptoms=p[6], causes=p[4], prevention=kb.PEST_IPM[p[5]],
         management=kb.PEST_IPM[p[5]], keywords=f"{p[2]};{p[3]}")
for code_, en, ta, s_en, s_ta, s_tl in kb.DEFICIENCIES:
    for lg, sym in (("en", s_en), ("ta", s_ta), ("tanglish", s_tl)):
        krec(f"KB_DEF_{code_}_{lg}", "all", "fertilizer", "nutrient_deficiency", {"en": "english", "ta": "tamil"}.get(lg, "tanglish"),
             en if lg != "ta" else ta, sym, symptoms=sym, management="Confirm with soil/leaf test; get corrective product and dose from the agriculture office.",
             keywords=f"{en};{ta}")
for f_ in kb.FERTILIZERS:
    krec(f"KB_FERT_{f_[0]}", "all", "fertilizer", f_[3], "english", f_[1], f"{f_[1]} ({f_[3]}). Nutrient content: {f_[4]}. {f_[5]}", keywords=f"{f_[1]};{f_[2]}")
for b in kb.BIO_AND_IPM:
    krec(f"KB_IPM_{b[0]}", "all", "pest_management", b[2], "english", b[1], f"{b[1]} — {b[2]}. Targets: {b[3]}. Use: {b[4]}", keywords=b[1])
for m in kb.IRRIGATION_METHODS:
    krec(f"KB_IRR_{m[0]}", "all", "irrigation", "method", "english", m[1], f"{m[2]} {m[3]}", keywords=m[1])
for s in kb.SOILS:
    krec(f"KB_SOIL_{s[0]}", "all", "soil", s[0], "english", s[1], f"{s[3]} Suitable crops: {s[4]}. Management: {s[5]}", keywords=f"{s[1]};{s[2]}")
for sc in kb.SCHEMES:
    krec(f"KB_SCH_{sc[0]}", "all", "scheme", sc[2], "english", sc[1], f"{sc[4]} Eligibility: {sc[3]} Apply: {sc[6]}",
         keywords=sc[1], st="scheme_summary_from_official_sources")
KCOLS = ["knowledge_id", "crop", "topic", "subtopic", "language", "title", "content", "symptoms", "causes", "prevention",
         "management", "keywords", "source_type", "verification_required"]
wcsv(f"{OUT}/knowledge/agricultural_knowledge.csv", K, KCOLS)
wjson(f"{OUT}/knowledge/agricultural_knowledge.json", K)

wcsv(f"{OUT}/knowledge/crops.csv", [dict(crop_id=c, name_en=v[0], name_ta=v[1], tanglish_names=";".join(v[2]), scientific_name=v[3],
      crop_type=v[4], season=kb.SEASON[c][0], duration=kb.DURATION[c][0], soil=kb.SOIL[c], verification_required="true")
      for c, v in kb.CROPS.items()], ["crop_id", "name_en", "name_ta", "tanglish_names", "scientific_name", "crop_type", "season", "duration", "soil", "verification_required"])
wcsv(f"{OUT}/knowledge/diseases.csv", [dict(disease_id=d[0], crops=d[1], name_en=d[2], name_ta=d[3], pathogen_type=d[4], causal_agent=d[5],
      symptoms=d[6], favourable_conditions=d[7], prevention=kb.PATHOGEN_MGMT[d[4]][0], management=kb.PATHOGEN_MGMT[d[4]][1],
      image_class=d[8], verification_required="true") for d in kb.DISEASES],
     ["disease_id", "crops", "name_en", "name_ta", "pathogen_type", "causal_agent", "symptoms", "favourable_conditions", "prevention", "management", "image_class", "verification_required"])
wcsv(f"{OUT}/knowledge/pests.csv", [dict(pest_id=p[0], crops=p[1], name_en=p[2], name_ta=p[3], scientific_name=p[4], pest_type=p[5],
      damage_symptoms=p[6], ipm=kb.PEST_IPM[p[5]], verification_required="true") for p in kb.PESTS],
     ["pest_id", "crops", "name_en", "name_ta", "scientific_name", "pest_type", "damage_symptoms", "ipm", "verification_required"])
wcsv(f"{OUT}/knowledge/fertilizers.csv", [dict(fertilizer_id=f_[0], name_en=f_[1], name_ta=f_[2], type=f_[3], nutrient_content=f_[4],
      use=f_[5], dose_guidance="Not provided — use soil test and agriculture office recommendation", verification_required="true") for f_ in kb.FERTILIZERS],
     ["fertilizer_id", "name_en", "name_ta", "type", "nutrient_content", "use", "dose_guidance", "verification_required"])
wcsv(f"{OUT}/knowledge/pesticides.csv", [dict(pesticide_id=b[0], name=b[1], type=b[2], targets=b[3], usage_notes=b[4],
      dose="Not provided — follow product label and agriculture officer/KVK advice",
      safety_notes="Wear gloves and mask; keep away from children, water sources and food; observe pre-harvest interval.",
      verification_required="true") for b in kb.BIO_AND_IPM],
     ["pesticide_id", "name", "type", "targets", "usage_notes", "dose", "safety_notes", "verification_required"])
irr = [dict(record_id=f"IRR_{m[0]}", crop="all", topic="method", name=m[1], description=m[2], notes=m[3], verification_required="true") for m in kb.IRRIGATION_METHODS]
irr += [dict(record_id=f"IRR_{c}", crop=c, topic="crop_water_need", name=kb.CROPS[c][0], description=kb.WATER[c], notes="", verification_required="true") for c in kb.CROPS]
wcsv(f"{OUT}/knowledge/irrigation.csv", irr, ["record_id", "crop", "topic", "name", "description", "notes", "verification_required"])
wcsv(f"{OUT}/knowledge/soil.csv", [dict(record_id=s[0], name_en=s[1], name_ta=s[2], description=s[3], suitable_crops=s[4], management=s[5],
      verification_required="true") for s in kb.SOILS], ["record_id", "name_en", "name_ta", "description", "suitable_crops", "management", "verification_required"])
wcsv(f"{OUT}/knowledge/schemes.csv", [dict(scheme_id=s[0], scheme_name=s[1], state=s[2], eligibility=s[3], benefits=s[4], documents=s[5],
      application_process=s[6], official_source=s[7], last_verified=s[8] or "not re-verified in this build",
      verification_required="true") for s in kb.SCHEMES],
     ["scheme_id", "scheme_name", "state", "eligibility", "benefits", "documents", "application_process", "official_source", "last_verified", "verification_required"])

# ------------------------------------------------------------------ vision
wcsv(f"{OUT}/vision/image_classes.csv", [dict(class_id=i, class_name=c[0], crop=c[1], disease=c[2], description=c[3], symptoms=c[4], severity=c[5])
      for i, c in enumerate(kb.IMAGE_CLASSES)], ["class_id", "class_name", "crop", "disease", "description", "symptoms", "severity"])
wcsv(f"{OUT}/vision/image_dataset_manifest.csv", [], ["image_id", "image_path", "crop", "label", "split", "source", "license", "verified"])
os.makedirs(f"{OUT}/tools", exist_ok=True)
shutil.copy("build_manifest.py", f"{OUT}/tools/build_manifest.py")

# ------------------------------------------------------------------ voice
voice = []
by_lang = defaultdict(list)
for r in rows:
    if r["noise_type"] == "none" and r["intent"] not in ("out_of_domain",) and r["language"] in ("english", "tamil", "tanglish"):
        by_lang[r["language"]].append(r)
noise_levels = ["clean", "low", "medium", "high"]
styles = ["normal", "fast", "slow", "rural_accent"]
n = 0
for lg, lst in by_lang.items():
    for r in random.sample(lst, min(100, len(lst))):
        n += 1
        voice.append(dict(id=f"VQ{n:04d}", transcript=r["text"], language=lg, script=r["script"], crop=r["crop"], intent=r["intent"],
                          audio_path=f"audio/{r['split']}/VQ{n:04d}.wav", speaker_id="SPK_TBD", noise_level=noise_levels[n % 4],
                          expected_text=norm_key(r["text"]), speaking_style=styles[n % 4], length="short",
                          recording_status="not_recorded", source_query_id=r["id"]))
LONG_PREFIX = {"english": "I am a farmer from Thanjavur, I have two acres, ", "tamil": "நான் தஞ்சாவூர் விவசாயி, எனக்கு ரெண்டு ஏக்கர் இருக்கு, ",
               "tanglish": "naan thanjavur la irundhu pesuren, rendu acre iruku, "}
for lg, lst in by_lang.items():
    for r in random.sample(lst, min(20, len(lst))):
        n += 1
        t = LONG_PREFIX[lg] + r["text"]
        voice.append(dict(id=f"VQ{n:04d}", transcript=t, language=lg, script=script_of(t), crop=r["crop"], intent=r["intent"],
                          audio_path=f"audio/{r['split']}/VQ{n:04d}.wav", speaker_id="SPK_TBD", noise_level=noise_levels[n % 4],
                          expected_text=norm_key(t), speaking_style=styles[n % 4], length="long",
                          recording_status="not_recorded", source_query_id=r["id"]))
wcsv(f"{OUT}/voice/voice_queries.csv", voice, ["id", "transcript", "language", "script", "crop", "intent", "audio_path", "speaker_id",
     "noise_level", "expected_text", "speaking_style", "length", "recording_status", "source_query_id"])

# ------------------------------------------------------------------ templates
tpl = {}
for k, lst in L.TEMPLATES.items():
    tpl[k] = [dict(id=f"TPL_{k}" if i == 0 else f"TPL_{k}_{i}", **v) for i, v in enumerate(lst)]
tpl_count = sum(len(v) * 3 for v in L.TEMPLATES.values())
wjson(f"{OUT}/responses/response_templates.json", {"_note": "Placeholders like {crop} are filled from the knowledge base. Never generate free text for doses.",
      "template_count": tpl_count, "templates": tpl})

# ------------------------------------------------------------------ validation report
lang_c = Counter(r["language"] for r in rows)
split_c = Counter(r["split"] for r in rows)
int_c = Counter(r["intent"] for r in rows)
crop_c = Counter(r["crop"] for r in rows if r["crop"])
REQ = ["id", "text", "language", "script", "intent", "topic", "normalized_text", "difficulty", "noise_type", "expected_response_type", "response_id", "split"]
missing = sum(1 for r in rows for c in REQ if not str(r.get(c, "")).strip())
ALLOWED = dict(language={"english", "tamil", "tanglish", "mixed"}, script={"latin", "tamil", "mixed"},
               difficulty={"easy", "medium", "hard"}, split={"train", "validation", "test"},
               noise_type={"none", "spelling_error", "short_query", "phonetic", "missing_words", "mixed_language", "farmer_slang", "voice_transcription_error"})
invalid = sum(1 for r in rows for c, a in ALLOWED.items() if r[c] not in a)
invalid += sum(1 for r in rows if r["intent"] not in S.INTENTS and r["intent"] != "out_of_domain")
dups = len(rows) - len({norm_key(r["text"]) for r in rows})
kb_ids = {k["knowledge_id"] for k in K}
dangling = sum(1 for r in rows if r["response_id"].startswith("KB_") and r["response_id"] not in kb_ids)
tot = len(rows)
report = {
 "total_rows_farmer_queries": tot, "total_intents": len(S.INTENTS) + 1, "total_crops": len(kb.CROPS),
 "total_diseases": len(kb.DISEASES), "total_pests": len(kb.PESTS), "total_tanglish_terms": len(LEXE),
 "language_percent": {k: round(100 * v / tot, 1) for k, v in sorted(lang_c.items())},
 "training_rows": split_c["train"], "validation_rows": split_c["validation"], "testing_rows": split_c["test"],
 "out_of_domain_rows_in_farmer_queries": int_c["out_of_domain"], "out_of_domain_file_rows": len(ood_out),
 "intent_examples_rows": len(ie2), "spelling_variation_rows": len(sv), "knowledge_records": len(K),
 "knowledge_records_by_language": dict(Counter(k["language"] for k in K)), "response_templates": tpl_count,
 "voice_metadata_rows": len(voice), "duplicate_count": dups, "potential_leakage_before_fix": len(leak_before),
 "potential_leakage_after_fix": len(leak_after), "missing_values_in_required_fields": missing,
 "invalid_records": invalid, "dangling_response_ids": dangling,
 "rows_per_intent": dict(sorted(int_c.items(), key=lambda x: x[1])),
 "rows_per_crop": dict(sorted(crop_c.items(), key=lambda x: x[1])),
 "noise_type_counts": dict(Counter(r["noise_type"] for r in rows)),
 "difficulty_counts": dict(Counter(r["difficulty"] for r in rows)),
 "intents_below_40_rows": [k for k, v in int_c.items() if v < 40],
}
wjson(f"{OUT}/reports/validation_report.json", report)
wcsv(f"{OUT}/reports/leakage_candidates_before_fix.csv",
     [dict(eval_text=rows[i]["text"], train_text=rows[j]["text"], similarity=round(s, 3), action="eval group moved to train")
      for i, j, s in [(0,0,0)][:0]] + [dict(eval_text=a, train_text=b, similarity=round(c,3), action="eval group moved to train") for a,b,c in leak_before_txt_pairs], ["eval_text", "train_text", "similarity", "action"])
print(json.dumps({k: v for k, v in report.items() if k not in ("rows_per_intent", "rows_per_crop")}, ensure_ascii=False, indent=1))
print("intents:", report["rows_per_intent"])
print("crops:", report["rows_per_crop"])
