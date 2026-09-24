"""
Agricultural lexicons used for NLP processing (never for display).

  models/lexicon/tanglish_dictionary.json   505 Tanglish terms with spelling variants → English
  models/lexicon/tamil_normalization.json   Tamil-script words/phrases → English

Both come from datasets/ (copied by ai/training/train_intent.py) and are loaded once, lazily.
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, FrozenSet

LEXICON_DIR = Path(__file__).resolve().parents[2] / "models" / "lexicon"

# Everyday Tanglish function words that aren't farming terms but strongly signal Tanglish.
TANGLISH_FUNCTION_WORDS = frozenset({
    "enna", "yenna", "epdi", "eppadi", "eppo", "yeppo", "enga", "evlo", "evvalavu", "iruku", "irukku",
    "illa", "illai", "venum", "vendum", "vendam", "sollunga", "solunga", "panrathu", "pannanum",
    "pannalam", "pannalaam", "panna", "pannunga", "podanum", "podalama", "podalaam", "aguthu", "aagudhu",
    "aaguthu", "varuthu", "varudhu", "romba", "konjam", "naan", "nan", "ungal", "unga", "enaku", "enakku",
    "la", "le", "ku", "ukku", "kku", "oda", "ah", "nu", "dhan", "than", "thaan", "ippo", "inniku",
    "naalaiku", "seri", "sari", "anna", "akka", "ayya", "da", "machan", "nalla", "yen", "edhuku",
    "ethuku", "mathiri", "maari", "kedaikkum", "kidaikuma", "paathu", "pathi", "panren", "iruken",
})


# Tamil verb/case endings written in Latin letters ("pogudu", "aagala", "podanum", "kittu").
TANGLISH_ENDINGS = ("uthu", "udhu", "udu", "anum", "alaam", "alama", "agala", "aagala", "unga", "ungal",
                    "kittu", "kitta", "pannu", "iruku", "irukku", "varala", "poguthu", "pogudhu")


@lru_cache(maxsize=1)
def english_stop_words() -> FrozenSet[str]:
    """English function words: never re-interpreted as Tanglish ("i" is not ஈ/fly)."""
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    return frozenset(ENGLISH_STOP_WORDS) | {"i", "im", "ive", "sir", "pls", "plz", "ok", "okay"}


# Tanglish pest/disease names missing from the dataset lexicon (official Tamil names, romanised).
_TANGLISH_SUPPLEMENT = {
    "kulai": "blast", "kulainoi": "blast", "kandamiruga": "rhinoceros", "kaandamiruga": "rhinoceros",
    "thandu": "stem", "thulaippan": "borer", "thulaipan": "borer", "pugaiyaan": "brown plant hopper",
    "pugaiyan": "brown plant hopper", "sevvazhugal": "red rot",
}


@lru_cache(maxsize=1)
def tanglish_lookup() -> Dict[str, str]:
    """Tanglish variant → English meaning (lowercase keys)."""
    data = json.loads((LEXICON_DIR / "tanglish_dictionary.json").read_text(encoding="utf-8"))
    lookup: Dict[str, str] = {}
    for entry in data.get("entries", []):
        english = entry.get("english") or []
        meaning = english[0] if isinstance(english, list) and english else str(english or "")
        for variant in [entry.get("term", ""), *entry.get("variations", [])]:
            variant = variant.strip().lower()
            if variant and meaning and variant not in lookup:
                lookup[variant] = meaning.lower()
    for variant, meaning in (data.get("lookup") or {}).items():
        lookup.setdefault(variant.strip().lower(), str(meaning).lower())
    for variant, meaning in _TANGLISH_SUPPLEMENT.items():
        lookup.setdefault(variant, meaning)
    return lookup


# Formal/written Tamil forms the (colloquial) dataset lexicon lacks; common in typed and transcribed questions.
_TAMIL_SUPPLEMENT = {
    "வேண்டும்": "need", "செய்ய": "do", "செய்வது": "do", "என்ன செய்ய வேண்டும்": "what to do",
    "மாறுகின்றன": "are turning", "மாறுகிறது": "is turning", "போட": "apply", "போடுவது": "apply",
    "கட்டுப்படுத்துவது": "control", "கட்டுப்படுத்த": "control", "தாக்குதல்": "attack",
}


@lru_cache(maxsize=1)
def tamil_lookup() -> Dict[str, str]:
    """Tamil word/phrase → English meaning."""
    data = json.loads((LEXICON_DIR / "tamil_normalization.json").read_text(encoding="utf-8"))
    mapping = data.get("map", data)
    table = {k.strip(): str(v).lower() for k, v in mapping.items() if not k.startswith("_") and isinstance(v, str)}
    for key, value in _TAMIL_SUPPLEMENT.items():
        table.setdefault(key, value)
    return table


@lru_cache(maxsize=1)
def english_vocabulary() -> FrozenSet[str]:
    """English words that appear as lexicon meanings — used to avoid mistaking English for Tanglish."""
    words = set()
    for meaning in list(tanglish_lookup().values()) + list(tamil_lookup().values()):
        words.update(meaning.split())
    return frozenset(words)
