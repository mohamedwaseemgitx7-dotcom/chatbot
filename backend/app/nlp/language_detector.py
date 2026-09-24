"""
Detects the language a farmer wrote in, so the answer can be given in the same language.

  tamil     Tamil script dominates
  tanglish  Tamil written in Latin letters ("nel la poochi iruku")
  mixed     Tamil script together with a substantial amount of Latin text
  english   everything else
"""
import re

from app.nlp.lexicon import TANGLISH_ENDINGS, TANGLISH_FUNCTION_WORDS, english_stop_words, english_vocabulary, tanglish_lookup
from app.nlp.normalizer import clean_text

TAMIL_CHAR = re.compile(r"[஀-௿]")
LATIN_CHAR = re.compile(r"[a-z]")

# Common English words that also appear in the Tanglish lexicon; they alone don't make a message Tanglish.
_ENGLISH_COMMON = frozenset({
    "a", "an", "the", "is", "are", "am", "to", "in", "on", "of", "for", "and", "or", "my", "i", "me", "it",
    "what", "why", "how", "when", "where", "which", "who", "can", "do", "does", "should", "will", "with",
    "this", "that", "there", "have", "has", "not", "no", "yes", "please", "tell", "about", "much", "many",
    "crop", "leaf", "leaves", "plant", "water", "rice", "paddy", "seed", "soil", "pest", "price", "rain",
})


def detect_language(text: str) -> str:
    cleaned = clean_text(text)
    tamil = len(TAMIL_CHAR.findall(cleaned))
    latin = len(LATIN_CHAR.findall(cleaned))
    if tamil + latin == 0:
        return "english"

    tamil_share = tamil / (tamil + latin)
    if tamil_share >= 0.6:
        return "tamil"
    if tamil_share >= 0.15:
        return "mixed"

    words = [w for w in cleaned.split() if LATIN_CHAR.search(w)]
    if not words:
        return "english"
    lexicon, english, stop = tanglish_lookup(), english_vocabulary(), english_stop_words()
    hits = sum(
        1 for w in words
        if w not in stop and (
            w in TANGLISH_FUNCTION_WORDS
            or (w in lexicon and w not in english and w not in _ENGLISH_COMMON)
            or (len(w) >= 5 and w.endswith(TANGLISH_ENDINGS))
        )
    )
    if hits and (len(words) <= 3 or hits / len(words) >= 0.2):
        return "tanglish"
    return "english"


def response_language(language: str) -> str:
    """Mixed Tamil-script/Latin messages get a Tanglish reply (how such farmers usually write)."""
    return "tanglish" if language == "mixed" else language
