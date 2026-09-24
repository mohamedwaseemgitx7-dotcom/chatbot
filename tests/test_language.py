import pytest

from app.nlp.language_detector import detect_language, response_language
from app.nlp.tanglish import to_english


@pytest.mark.parametrize("text, expected", [
    ("How can I control pests in rice?", "english"),
    ("My rice leaves are turning yellow", "english"),
    ("நெல் இலை மஞ்சளாகுது ஏன்?", "tamil"),
    ("என் நெல் இலைகள் மஞ்சளாகின்றன", "tamil"),
    ("nel la poochi iruku enna panrathu", "tanglish"),
    ("nellu ilai manjala iruku enna panrathu", "tanglish"),
    ("nelku uram?", "tanglish"),
    ("tomato la poochi romba iruku", "tanglish"),
])
def test_detects_language(text, expected):
    assert detect_language(text) == expected


def test_mixed_script_replies_in_tanglish():
    detected = detect_language("nel crop la இலை yellow ah irukku")
    assert detected in {"mixed", "tanglish"}
    assert response_language("mixed") == "tanglish"


def test_english_function_words_are_not_tanglish():
    # "i" is also Tanglish for ஈ (fly) — it must stay "i" in English text.
    assert to_english("How can I control pests") == "how can i control pests"


def test_normalises_tamil_and_tanglish_to_english_terms():
    assert "paddy" in to_english("நெல்லுக்கு எந்த உரம் போடணும்")
    assert "fertilizer" in to_english("நெல்லுக்கு எந்த உரம் போடணும்")
    english = to_english("nel ilai manjala iruku")
    assert "paddy" in english and "leaf" in english and "yellow" in english


def test_manjal_means_yellow_with_leaf_context_else_turmeric():
    assert "yellow" in to_english("ilai manjal")
    assert "turmeric" in to_english("manjal vilai")
