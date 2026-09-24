import json
from pathlib import Path

import pytest

from app.nlp.confidence import gate
from app.nlp.entities import detect_crop
from app.nlp.intent_classifier import predict_intents
from app.nlp.tanglish import to_english

REPORT = Path(__file__).resolve().parents[1] / "reports" / "intent_report.json"


def top_intent(text):
    return predict_intents(text, to_english(text))[0][0]


@pytest.mark.parametrize("text, intent", [
    ("How can I control pests in rice?", "pest_attack"),
    ("நெல் இலை மஞ்சளாகுது ஏன்?", "yellow_leaf"),
    ("nelku uram?", "fertilizer"),
    ("today tomato price", "market_price"),
    ("hi", "greeting"),
])
def test_known_intents(text, intent):
    assert top_intent(text) == intent


@pytest.mark.parametrize("text", ["Write Python code", "who is the prime minister", "tell me a movie story", "what is bitcoin"])
def test_out_of_domain_is_refused(text):
    english = to_english(text)
    decision = gate(predict_intents(text, english), text, english, detect_crop(text, english))
    assert decision.decision == "out_of_domain"


def test_farming_question_is_not_refused():
    text = "my paddy leaves have brown spots"
    english = to_english(text)
    decision = gate(predict_intents(text, english), text, english, detect_crop(text, english))
    assert decision.decision in {"answer", "clarify"}


@pytest.mark.parametrize("text, crop", [
    ("nel la poochi", "paddy"), ("நெல்லுக்கு உரம்", "paddy"), ("thakkali ilai", "tomato"),
    ("milagai leaf curl", "chilli"), ("vazhai", "banana"), ("how to grow maize", "maize"), ("what is fertilizer", None),
])
def test_crop_detection(text, crop):
    assert detect_crop(text, to_english(text)) == crop


def test_held_out_accuracy_is_recorded_and_above_floor():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["test_accuracy"] >= 0.75
    assert report["out_of_domain_recall"] >= 0.9
