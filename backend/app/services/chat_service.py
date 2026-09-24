"""
Chat pipeline:

  message → language detection → Tamil/Tanglish normalisation → crop detection → sentence embedding
          → intent classification → domain/confidence gate → retrieval (verified knowledge, threshold)
          → controlled response in the farmer's language (+ sources)

Every stage degrades gracefully: if a model is missing the farmer gets a controlled message, never a crash
or an invented answer. CPU-bound; call it from a threadpool.
"""
import logging
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional

from app.embeddings.embedder import EmbeddingUnavailable, embed_one
from app.embeddings.vector_store import load_store
from app.nlp.confidence import gate
from app.nlp.entities import detect_crop
from app.nlp.intent_classifier import IntentModelUnavailable, predict_intents
from app.nlp.language_detector import detect_language, response_language
from app.nlp.tanglish import to_english
from app.rag.response_engine import SCHEME_INTENTS, compose_answer, sources_of, template
from app.rag.retriever import retrieve, specific_terms, topics_for_intent

TAMIL_SCRIPT = re.compile(r"[஀-௿]")

logger = logging.getLogger(__name__)

# Intents whose answer depends on which crop it is.
CROP_SPECIFIC = {"pest", "disease", "protection", "nutrient"}


@dataclass
class ChatResult:
    response: str
    language: str
    intent: str
    confidence: float
    status: str  # answered | out_of_domain | clarification | no_knowledge | conversational | guidance | unavailable
    crop: Optional[str] = None
    sources: List[dict] = field(default_factory=list)
    timings_ms: dict = field(default_factory=dict)


def answer(message: str) -> ChatResult:
    started = time.perf_counter()
    text = message.strip()
    detected = detect_language(text)
    language = response_language(detected)
    english = to_english(text)
    crop = detect_crop(text, english)

    try:
        vector = embed_one(english)
        intents = predict_intents(text, english, vector)
    except (EmbeddingUnavailable, IntentModelUnavailable):
        logger.error("NLP models unavailable")
        return ChatResult(template("no_knowledge", language), language, "unavailable", 0.0, "unavailable", crop)
    nlp_ms = (time.perf_counter() - started) * 1000

    decision = gate(intents, text, english, crop)
    intent, confidence = decision.intent, round(decision.confidence, 3)

    def result(response, status, sources=None):
        return ChatResult(response, language, intent, confidence, status, crop, sources or [],
                          {"nlp": round(nlp_ms, 1), "total": round((time.perf_counter() - started) * 1000, 1)})

    if decision.decision == "out_of_domain":
        return result(template("out_of_domain", language), "out_of_domain")
    if decision.decision == "conversational":
        return result(template(intent, language), "conversational")
    if decision.decision == "clarify":
        return result(template("clarify", language), "clarification")
    if intent in ("market_price", "weather", "image_upload_help"):
        return result(template(intent, language), "guidance")

    # Naming terms are matched against record titles in the SAME script: English titles ← words of the English
    # normalisation; Tamil titles ← Tamil-script words the farmer typed. (Mixing them made raw Tanglish filler
    # like "enna"/"pannanum" count as disease names, so nothing matched.)
    terms = specific_terms(english)
    tamil_terms = {t for t in specific_terms(text) if TAMIL_SCRIPT.search(t)}
    # Tamil questions: prefer the official Tamil pages; otherwise fall back to English records.
    if language == "tamil":
        tamil_hits = retrieve(vector, crop=crop, intent=intent, language="tamil", terms=tamil_terms)
        if tamil_hits:
            records = [h.record for h in tamil_hits]
            return result(compose_answer(records, language), "answered", sources_of(records))
    hits = retrieve(vector, crop=crop, intent=intent, terms=terms)
    if hits:
        records = [h.record for h in hits]
        store = load_store()
        return result(compose_answer(records, language, store.tamil_by_pair if store else None), "answered", sources_of(records))

    if intent in SCHEME_INTENTS:
        return result(template("scheme", language), "guidance")
    if crop is None and topics_for_intent(intent) & CROP_SPECIFIC:
        return result(template("need_crop", language), "clarification")
    return result(template("no_knowledge", language), "no_knowledge")
