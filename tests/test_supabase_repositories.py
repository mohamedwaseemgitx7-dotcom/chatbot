"""
Live Supabase checks (they create and delete a temporary user). Opt in with RUN_SUPABASE_TESTS=1.
"""
import os
import uuid

import pytest

from app.database.supabase import check_database, get_supabase_client, is_configured

pytestmark = pytest.mark.skipif(
    not (os.environ.get("RUN_SUPABASE_TESTS") == "1" and is_configured()), reason="set RUN_SUPABASE_TESTS=1 to run live Supabase tests"
)


@pytest.fixture
def temp_user():
    client = get_supabase_client()
    user = client.auth.admin.create_user({"email": f"pytest-{uuid.uuid4().hex[:8]}@example.test", "password": uuid.uuid4().hex, "email_confirm": True}).user
    yield client, user.id
    client.auth.admin.delete_user(user.id)


def test_database_connected():
    assert check_database() == "connected"


def test_repositories_round_trip(temp_user):
    from app.database.repositories.conversation_repo import conversation_belongs_to
    from app.database.repositories.image_repo import save_image_prediction
    from app.database.repositories.message_repo import save_message

    client, user_id = temp_user
    conversation = client.table("conversations").insert({"user_id": user_id, "title": "pytest"}).execute().data[0]["id"]
    assert conversation_belongs_to(conversation, user_id)
    assert not conversation_belongs_to(conversation, str(uuid.uuid4()))
    message = save_message(conversation, "user", "நெல் இலை மஞ்சளாகுது", language="tamil", message_type="image")
    assert save_image_prediction(message, f"{user_id}/{conversation}/x.png", crop="paddy", prediction="brown spot", confidence=0.8)
    with pytest.raises(ValueError):
        save_message(conversation, "bot", "x")


def test_knowledge_is_readable_but_not_writable_by_anon():
    import httpx

    from app.config.settings import get_settings

    s = get_settings()
    headers = {"apikey": s.SUPABASE_ANON_KEY, "Content-Type": "application/json"}
    assert httpx.get(f"{s.SUPABASE_URL}/rest/v1/knowledge?select=id&limit=1", headers=headers).status_code == 200
    # Columns from the base schema only, so the request reaches Row Level Security (not a schema error).
    denied = httpx.post(f"{s.SUPABASE_URL}/rest/v1/knowledge", headers=headers,
                        json={"crop": "paddy", "topic": "pest", "title": "x", "content": "x"})
    assert denied.status_code in (401, 403)
