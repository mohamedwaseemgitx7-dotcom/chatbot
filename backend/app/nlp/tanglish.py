"""
Tamil / Tanglish → English normalisation for the NLP pipeline (classification + retrieval).

Farmers' words are mapped to English farming terms so one English model can handle all three
languages. Output is internal only; the chat always shows the farmer's original text.
"""
import difflib
import re
from functools import lru_cache

from app.nlp.lexicon import english_stop_words, tamil_lookup, tanglish_lookup
from app.nlp.normalizer import clean_text

# Tamil case/postposition endings, longest first (e.g. நெல்லுக்கு → நெல், இலையில → இலை).
_TAMIL_SUFFIXES = sorted([
    "க்கு", "ுக்கு", "க்கா", "ுக்கா", "இல்", "ில்", "ில", "ல்ல", "லே", "ல", "ை", "ையை", "ும்", "ுல", "ோட",
    "ுடைய", "ிடம்", "ால", "ால்", "ாக", "ா", "ு", "ங்க", "கள்", "களை", "களுக்கு", "த்து", "த்தை", "த்தில்",
], key=len, reverse=True)

_LEAF_CONTEXT = {"ilai", "elai", "leaf", "leaves", "இலை", "இலைகள்", "இலையில", "இலையில்", "yellow"}
# Fuzzy matching may only land on content words — never on grammar that changes meaning
# (வேண்டும் "need" must not become வேண்டாம் "don't want").
_NO_FUZZY_MEANINGS = {"don't want", "need", "no", "what", "which", "why", "how", "when", "where", "who", "okay",
                      "there is", "is coming", "need to do", "can do", "please tell", "is it possible", "went"}


@lru_cache(maxsize=1)
def _tamil_phrases():
    table = tamil_lookup()
    longest = max((len(k.split()) for k in table), default=1)
    return table, longest


# Letters speech recognisers (and farmers typing) often swap: ள/ழ→ல, ண/ந→ன, ற→ர.
_TAMIL_FOLD = str.maketrans({"ள": "ல", "ழ": "ல", "ண": "ன", "ந": "ன", "ற": "ர"})


def _fold(word: str) -> str:
    return word.translate(_TAMIL_FOLD)


@lru_cache(maxsize=1)
def _folded_tamil():
    table = tamil_lookup()
    folded = {}
    for key, meaning in table.items():
        folded.setdefault(_fold(key), meaning)
    return folded, sorted(k for k in folded if " " not in k and len(k) >= 3)


@lru_cache(maxsize=1)
def _latin_vocabulary():
    return sorted(k for k in tanglish_lookup() if len(k) >= 4)


def _tamil_word(word: str, table: dict) -> str | None:
    folded, vocabulary = _folded_tamil()
    candidates = [word]
    for suffix in _TAMIL_SUFFIXES:  # strip one inflection and retry
        if word.endswith(suffix) and len(word) - len(suffix) >= 2:
            stem = word[: -len(suffix)]
            candidates += [stem, stem + "்"]
    for candidate in candidates:
        if candidate in table:
            return table[candidate]
    for candidate in candidates:  # letter-confusion tolerant (மஞ்சலாக → மஞ்சளா)
        if _fold(candidate) in folded:
            return folded[_fold(candidate)]
    if len(word) >= 5:  # last resort: close spelling (ASR errors such as பூச்சி → போச்சி)
        target = _fold(word)
        close = difflib.get_close_matches(target, vocabulary, n=1, cutoff=0.85)
        if close and folded[close[0]] not in _NO_FUZZY_MEANINGS:
            return folded[close[0]]
        # compound words (போச்சியிருக்கு = பூச்சி + இருக்கு): a lexicon word at the start of this one
        best = None
        for key in vocabulary:
            if len(key) >= 6 and len(target) > len(key):
                if difflib.SequenceMatcher(None, target[: len(key)], key).ratio() >= 0.8 and (best is None or len(key) > len(best)):
                    best = key
        if best and folded[best] not in _NO_FUZZY_MEANINGS:
            return folded[best]
    return None


def _latin_word(word: str, lookup: dict) -> str | None:
    if word in english_stop_words():
        return None
    if word in lookup:
        return lookup[word]
    if len(word) >= 6 and not word.isdigit():  # spelling mistakes: "poochiii", "urammm", "thannii"
        close = difflib.get_close_matches(word, _latin_vocabulary(), n=1, cutoff=0.86)
        if close:
            return lookup[close[0]]
    return None


# Tanglish phrases whose meaning differs from their words ("kulai" alone is read as "pipe").
_TANGLISH_PHRASES = {
    "kulai noi": "blast disease", "kulai noai": "blast disease", "kulai nooi": "blast disease",
    "kandamiruga vandu": "rhinoceros beetle", "kaandamiruga vandu": "rhinoceros beetle",
    "thandu thulaippan": "stem borer", "thandu thulaipan": "stem borer", "vellai ee": "whitefly",
}
_PHRASE_PATTERN = re.compile(r"\b(" + "|".join(map(re.escape, sorted(_TANGLISH_PHRASES, key=len, reverse=True))) + r")\b")


def to_english(text: str) -> str:
    """Maps Tamil and Tanglish words to English; English words pass through unchanged."""
    words = _PHRASE_PATTERN.sub(lambda m: _TANGLISH_PHRASES[m.group(1)], clean_text(text)).split()
    table, longest = _tamil_phrases()
    lookup = tanglish_lookup()
    has_leaf_context = any(w in _LEAF_CONTEXT for w in words)
    out: list[str] = []
    i = 0
    while i < len(words):
        # Longest Tamil phrase first ("மண் பரிசோதனை" → "soil test").
        matched = False
        for size in range(min(longest, len(words) - i), 1, -1):
            phrase = " ".join(words[i : i + size])
            if phrase in table:
                out.append(table[phrase])
                i += size
                matched = True
                break
        if matched:
            continue

        word = words[i]
        # manjal/மஞ்சள் is both "yellow" and "turmeric": leaf context means yellow.
        if word in {"manjal", "manjala", "manjalaa", "மஞ்சள்", "மஞ்சளா"}:
            out.append("yellow" if has_leaf_context or word.endswith(("a", "ா")) else "turmeric")
        else:
            is_tamil = any("஀" <= ch <= "௿" for ch in word)
            mapped = _tamil_word(word, table) if is_tamil else _latin_word(word, lookup)
            out.append(mapped if mapped else word)
        i += 1
    if "turmeric" in out and ({"leaf", "leaves"} & set(" ".join(out).split()) or has_leaf_context):
        out = ["yellow" if w == "turmeric" else w for w in out]  # மஞ்சள் next to "leaf" is the colour
    return " ".join(out)


def normalize_tanglish(text: str) -> str:
    """Kept for callers of the old API."""
    return to_english(text)
