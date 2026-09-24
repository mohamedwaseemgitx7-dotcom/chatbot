"""
Text cleaning shared by language detection, intent classification and retrieval.
The farmer's original message is never modified for display — this output is for NLP only.
"""
import re
import unicodedata

_TAMIL = r"஀-௿"
_NOT_WORD = re.compile(rf"[^a-z0-9{_TAMIL}\s]")
_ELONGATED = re.compile(r"([a-z])\1{2,}")  # "hiiiii" → "hii", "pleaseee" → "pleasee"
_SPACES = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """Unicode-normalised, lowercase, punctuation-free, single-spaced text."""
    text = unicodedata.normalize("NFC", text or "").lower()
    text = text.replace("’", "'").replace("'", "")
    text = _NOT_WORD.sub(" ", text)
    text = _ELONGATED.sub(r"\1\1", text)
    return _SPACES.sub(" ", text).strip()


def normalize_text(text: str, language: str = "") -> str:
    """Kept for callers of the old API: returns clean_text(text)."""
    return clean_text(text)


def tokens(text: str) -> list[str]:
    return clean_text(text).split()
