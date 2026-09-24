import pytest

from app.embeddings.embedder import embed_one
from app.embeddings.vector_store import load_store
from app.nlp.tanglish import to_english
from app.rag.response_engine import compose_answer, excerpt
from app.rag.retriever import retrieve

store = load_store()
needs_index = pytest.mark.skipif(store is None or not store.records, reason="knowledge index not built")


def search(text, crop, intent):
    return retrieve(embed_one(to_english(text)), crop=crop, intent=intent)


@needs_index
def test_every_served_record_has_an_official_source():
    for record in store.records:
        assert record["source_url"].startswith("https://agritech.tnau.ac.in/")
        assert record["retrieved_at"]
        assert record["verification_status"] in {"official_source_pending_review", "expert_verified"}


@needs_index
def test_retrieves_the_right_crop():
    hits = search("How to control stem borer in paddy", "paddy", "stem_borer")
    assert hits, "expected verified knowledge for paddy stem borer"
    assert hits[0].record["crop"] == "paddy"


@needs_index
def test_tanglish_question_reaches_the_same_knowledge():
    english = search("paddy stem borer control", "paddy", "stem_borer")
    tanglish = search("nel la thandu thulaippan poochi control", "paddy", "stem_borer")
    assert english and tanglish
    assert english[0].record["id"] in {h.record["id"] for h in tanglish}


@needs_index
def test_irrelevant_question_retrieves_nothing():
    assert search("how do I repair a car engine", None, "agri_general_info") == []


@needs_index
def test_answer_quotes_the_record_and_warns_about_chemicals():
    hits = search("How to control stem borer in paddy", "paddy", "stem_borer")
    text = compose_answer([h.record for h in hits], "english")
    assert excerpt(hits[0].record["content"], 200).split(" …")[0][:40] in text
    if hits[0].record["topic"] in {"pest", "disease", "protection"}:
        assert "agriculture officer" in text


def test_excerpt_never_cuts_mid_sentence():
    text = "First sentence here. " * 80
    cut = excerpt(text, 100)
    assert cut.endswith(" …") and cut[:-2].rstrip().endswith(".")
