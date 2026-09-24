import uuid

import pytest

from app.rag.response_engine import TEMPLATES


def chat(client, message, **extra):
    return client.post("/api/chat", json={"message": message, **extra})


@pytest.mark.parametrize("message, language", [
    ("How can I control pests in rice?", "english"),
    ("நெல் இலை மஞ்சளாகுது ஏன்?", "tamil"),
    ("nel la poochi iruku enna panrathu", "tanglish"),
    ("nellu ilai manjala iruku enna panrathu", "tanglish"),
])
def test_replies_in_the_same_language(client, message, language):
    body = chat(client, message).json()
    assert body["language"] == language
    assert body["response"]
    assert body["status"] in {"answered", "no_knowledge", "clarification", "guidance"}


def test_out_of_domain_refusal(client):
    body = chat(client, "Write Python code").json()
    assert body["status"] == "out_of_domain"
    assert body["response"] == "Sorry, I can help only with agriculture and farming-related questions."


def test_greeting_is_conversational(client):
    assert chat(client, "vanakkam").json()["status"] == "conversational"


def test_answers_are_never_invented(client):
    """Every reply is either a fixed template or built from retrieved records with sources."""
    templates = {text for per_language in TEMPLATES.values() for text in per_language.values()}
    for message in ["What is the best treatment for a disease not in the knowledge base?", "nelku uram?"]:
        body = chat(client, message).json()
        if body["status"] == "answered":
            assert body["sources"], "an answer must carry its sources"
            assert all(s["url"].startswith("https://") for s in body["sources"])
        else:
            assert body["response"] in templates


def test_conversation_id_is_echoed(client):
    cid = str(uuid.uuid4())
    assert chat(client, "hi", conversation_id=cid).json()["conversation_id"] == cid


@pytest.mark.parametrize("payload", [
    {"message": ""},
    {"message": "   \n\t "},
    {"message": "x" * 1001},
    {"message": "hi", "conversation_id": "not-a-uuid"},
    {},
])
def test_invalid_requests_are_rejected_cleanly(client, payload):
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Invalid request."
    assert "x" * 50 not in response.text  # submitted values are not echoed back


def test_non_json_body_is_rejected(client):
    response = client.post("/api/chat", content=b"not json", headers={"Content-Type": "application/json"})
    assert response.status_code == 422
