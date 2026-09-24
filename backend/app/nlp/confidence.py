"""
Domain guard + confidence gate. Decides *whether* to answer before anything is retrieved.

Three signals are combined (a single one is never trusted on its own):
  1. the intent classifier (including its out_of_domain class) and its confidence,
  2. agriculture vocabulary in the message (lexicons + crop names),
  3. retrieval similarity against the verified knowledge base (checked later, in the retriever).
"""
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.nlp.lexicon import tamil_lookup, tanglish_lookup

CONVERSATIONAL = {"greeting", "thanks"}
OUT_OF_DOMAIN = "out_of_domain"

# English farming words (the lexicons cover Tamil/Tanglish; their English meanings are added below).
_AGRI_WORDS = {
    "crop", "crops", "farm", "farming", "farmer", "field", "plant", "plants", "leaf", "leaves", "root", "stem", "seed",
    "seeds", "soil", "fertilizer", "fertiliser", "manure", "compost", "urea", "dap", "potash", "pest", "pests", "insect",
    "worm", "borer", "disease", "fungus", "spray", "pesticide", "insecticide", "irrigation", "water", "drip", "harvest",
    "yield", "sowing", "variety", "paddy", "rice", "tomato", "chilli", "banana", "coconut", "sugarcane", "groundnut",
    "cotton", "maize", "brinjal", "onion", "drumstick", "moringa", "turmeric", "gram", "pulses", "weed", "agriculture",
    "kisan", "subsidy", "scheme", "insurance", "mandi", "market", "rain", "drought", "wilt", "blight", "rot", "yellow",
    "nitrogen", "phosphorus", "potassium", "zinc", "cattle", "tractor", "nursery", "transplant", "mulch", "organic",
}
_WORD = re.compile(r"[a-z]+|[஀-௿]+")


def agriculture_terms(text: str, english: str) -> List[str]:
    """Farming words found in the message (original + normalised)."""
    tamil, tanglish = tamil_lookup(), tanglish_lookup()
    found = []
    for word in set(_WORD.findall(text.lower())) | set(_WORD.findall(english.lower())):
        if word in _AGRI_WORDS or word in tamil or (word in tanglish and len(word) > 2):
            found.append(word)
    return found


@dataclass
class Gate:
    decision: str  # "conversational" | "out_of_domain" | "answer" | "clarify"
    intent: str
    confidence: float
    agriculture_terms: List[str]


def gate(intents: List[Tuple[str, float]], text: str, english: str, crop: Optional[str]) -> Gate:
    top_intent, top_p = intents[0]
    terms = agriculture_terms(text, english)
    agri_signal = bool(terms) or crop is not None

    if top_intent == OUT_OF_DOMAIN:
        # Refuse outright only when there is no farming signal, or the classifier is very sure.
        # A farmer who names a crop gets a clarifying question rather than a refusal.
        if not agri_signal or top_p >= 0.9:
            return Gate("out_of_domain", top_intent, top_p, terms)
        second, second_p = intents[1] if len(intents) > 1 else (top_intent, top_p)
        return Gate("answer" if second_p >= 0.2 else "clarify", second, second_p, terms)

    if top_intent in CONVERSATIONAL and top_p >= 0.4:
        return Gate("conversational", top_intent, top_p, terms)

    if not agri_signal and top_p < 0.5:
        return Gate("out_of_domain", OUT_OF_DOMAIN, 1 - top_p, terms)

    if top_p < 0.25 and not crop:
        return Gate("clarify", top_intent, top_p, terms)
    return Gate("answer", top_intent, top_p, terms)


def is_confidence_sufficient(confidence: float, threshold: float = 0.70) -> bool:
    """Kept for callers of the old API."""
    return confidence >= threshold
