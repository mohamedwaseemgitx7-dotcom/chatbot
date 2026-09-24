"""
Retrieves verified knowledge for a question.

score = cosine(query, record)
        + CROP_MATCH_BONUS   when the record is about the crop the farmer named
        − CROP_MISMATCH_PENALTY when it is about a different crop
        + TOPIC_MATCH_BONUS  when the record's topic fits the predicted intent
Only records whose final score clears the similarity threshold are used; otherwise the bot says it
doesn't have enough verified information (it never falls back to guessing).
"""
import re
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from app.config.settings import get_settings
from app.embeddings.vector_store import load_store

CROP_MATCH_BONUS = 0.08
CROP_MISMATCH_PENALTY = 0.20
TOPIC_MATCH_BONUS = 0.05

# Which knowledge topics answer which intents.
INTENT_TOPICS = {
    "pest": {"pest_attack", "aphids", "whitefly", "stem_borer", "leaf_folder", "bollworm", "fruit_borer", "thrips_mites"},
    "disease": {"crop_disease", "leaf_spot", "leaf_blight", "leaf_curl", "root_rot", "fruit_rot", "wilting", "yellow_leaf"},
    "nutrient": {"fertilizer", "fertilizer_timing", "nitrogen_deficiency", "phosphorus_deficiency", "potassium_deficiency",
                 "micronutrient_deficiency", "organic_fertilizer", "yellow_leaf"},
    "irrigation": {"irrigation", "drip_irrigation", "water_shortage", "drought", "heat_stress"},
    "cultivation": {"sowing_time", "seed_selection", "seed_treatment", "harvesting", "post_harvest_storage", "agri_general_info",
                    "soil_health", "soil_ph", "soil_testing", "organic_farming", "rain_damage"},
}


def topics_for_intent(intent: str) -> set:
    topics = {topic for topic, intents in INTENT_TOPICS.items() if intent in intents}
    if topics & {"pest", "disease"}:
        topics.add("protection")  # crop-protection pages not labelled as pest or disease specifically
    return topics


@dataclass
class Retrieved:
    record: dict
    score: float
    similarity: float


# Words too generic to identify a specific pest/disease record.
_GENERIC = {
    "disease", "diseases", "pest", "pests", "insect", "insects", "control", "manage", "management", "symptoms",
    "symptom", "treatment", "damage", "attack", "what", "how", "why", "which", "when", "there", "does", "with",
    "leaf", "leaves", "plant", "plants", "crop", "crops", "field", "my", "the", "and", "for", "is", "are", "in", "of",
    "problem", "spray", "remedy", "solution", "tell", "please", "about", "coming", "turning", "infestation",
    "have", "has", "had", "get", "getting", "show", "showing", "can", "should", "this", "that", "very", "lot",
    "there is", "affected", "affecting", "found", "seen", "appear", "appearing", "need", "apply", "use",
    "come", "came", "comes", "appeared", "happened", "happening", "occurred", "started",  # Tanglish "vandhuruchu" etc.
    "paddy", "rice", "tomato", "chilli", "banana", "coconut", "sugarcane", "groundnut", "cotton", "maize", "brinjal",
    "onion", "drumstick", "turmeric", "blackgram", "greengram", "gram", "நோய்", "பூச்சி", "கட்டுப்பாடு", "அறிகுறிகள்",
}
TITLE_MATCH_BONUS = 0.08  # per specific query word found in the record title
TITLE_MATCH_CAP = 0.16
_WORD = re.compile(r"[a-z]{3,}|[஀-௿]{2,}")


# When the question names something specific (a pest/disease), the record must mention most of those names;
# otherwise only a very close semantic match may answer. Stops "yellow stem borer" → "Rice yellow dwarf".
MIN_TERM_COVERAGE = 0.5
HIGH_SIMILARITY = 0.75
# Words that describe (colour, plant part, symptom) rather than name a pest/disease: they still earn the
# title bonus, but only naming words must agree with the record title.
_DESCRIPTIVE = {
    "yellow", "brown", "black", "white", "red", "green", "grey", "gray", "purple", "orange", "dark", "pale",
    "spot", "rot", "rotting", "wilt", "wilting", "blight", "dry", "drying", "curl", "curling", "hole", "holes",
    "fruit", "stem", "root", "shoot", "flower", "pod", "grain", "bud", "seedling", "worm", "fly", "bug", "beetle",
    "small", "big", "inside", "young", "old", "new", "tip", "tips", "edge", "edges",
    "மஞ்சள்", "வெள்ளை", "கருப்பு", "சிவப்பு", "பழுப்பு", "இலை", "இலைகள்", "பழம்", "தண்டு", "வேர்", "புழு", "வண்டு", "அழுகல்",
}


def _crop_words() -> set:
    from app.nlp.entities import CROP_NAMES

    return {w for names in CROP_NAMES.values() for name in names for w in name.lower().split()}


def _stem(word: str) -> str:
    return word[:-1] if len(word) > 4 and word.endswith("s") and not word.endswith("ss") else word


def specific_terms(*texts: str) -> set:
    return {_stem(w) for t in texts for w in _WORD.findall((t or "").lower()) if w not in _GENERIC and _stem(w) not in _GENERIC}


def naming_terms(terms: set) -> set:
    """The subset of query terms that names something (pest/disease), not crop names or descriptions."""
    crops = _crop_words()
    return {t for t in terms if t not in _DESCRIPTIVE and t not in crops and t not in {"noi", "poochi", "la"}}


def term_coverage(title: str, terms: set) -> float:
    names = naming_terms(terms)
    return sum(1 for term in names if term in title) / len(names) if names else 1.0


def _title_bonus(store, terms: set) -> np.ndarray:
    """Exact names matter: "whitefly", "stem borer", குலை (in குலைநோய்) should win over merely similar records."""
    bonus = np.zeros(len(store.records), dtype=np.float32)
    if not terms:
        return bonus
    for i, title in enumerate(store.titles):
        hits = sum(1 for term in terms if term in title)
        bonus[i] = min(TITLE_MATCH_CAP, TITLE_MATCH_BONUS * hits)
    return bonus


def retrieve(query_vector: np.ndarray, *, crop: Optional[str], intent: str, top_k: int = 3,
             threshold: Optional[float] = None, language: str = "english", terms: Optional[set] = None) -> List[Retrieved]:
    store = load_store(language)
    if store is None:
        return []
    threshold = get_settings().RETRIEVAL_SIMILARITY_THRESHOLD if threshold is None else threshold

    similarity = store.vectors @ query_vector
    scores = similarity + _title_bonus(store, terms or set())
    if crop:
        same = store.crops == crop
        generic = store.crops == "general"
        scores[same] += CROP_MATCH_BONUS
        scores[~same & ~generic] -= CROP_MISMATCH_PENALTY
    wanted = topics_for_intent(intent)
    if wanted:
        scores[np.isin(store.topics, list(wanted))] += TOPIC_MATCH_BONUS

    results = []
    for i in np.argsort(scores)[::-1][: top_k * 3]:
        if scores[i] < threshold:
            break
        if terms and term_coverage(store.titles[i], terms) < MIN_TERM_COVERAGE and similarity[i] < HIGH_SIMILARITY:
            continue  # a similar-sounding record about something else
        results.append(Retrieved(store.records[i], float(scores[i]), float(similarity[i])))
        if len(results) == top_k:
            break
    return results


def retrieve_relevant_knowledge(embedding, intent: str, top_k: int = 3):
    """Kept for callers of the old API."""
    return [r.record for r in retrieve(np.asarray(embedding, dtype=np.float32), crop=None, intent=intent, top_k=top_k)]
