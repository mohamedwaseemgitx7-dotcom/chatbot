import pytest

from app.config.settings import get_settings
from app.security import auth
from conftest import TEST_PASSWORD, TEST_USER


def login(client, username=TEST_USER, password=TEST_PASSWORD):
    return client.post("/api/auth/login", json={"username": username, "password": password})


@pytest.mark.parametrize("path, method", [("/api/chat", "post"), ("/api/image/analyze", "post"), ("/api/voice/transcribe", "post"), ("/api/auth/me", "get")])
def test_protected_endpoints_need_a_token(anonymous_client, path, method):
    kwargs = {"json": {"message": "hi"}} if path == "/api/chat" else {}
    response = getattr(anonymous_client, method)(path, **kwargs)
    assert response.status_code == 401
    assert response.json() == {"detail": "Please log in again."}


def test_health_stays_public(anonymous_client):
    assert anonymous_client.get("/api/health").status_code == 200


def test_login_success_returns_token(anonymous_client):
    body = login(anonymous_client).json()
    assert body["username"] == TEST_USER and body["token"] and body["expires_at"]
    me = anonymous_client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert me.json()["username"] == TEST_USER


@pytest.mark.parametrize("username, password", [(TEST_USER, "wrong"), ("someone", TEST_PASSWORD), ("", "x")])
def test_bad_credentials_rejected(anonymous_client, username, password):
    response = login(anonymous_client, username, password)
    assert response.status_code in (401, 422)
    assert TEST_PASSWORD not in response.text


def test_username_is_case_insensitive(anonymous_client):
    assert login(anonymous_client, TEST_USER.upper()).status_code == 200


def test_tampered_or_forged_token_rejected(anonymous_client):
    token = login(anonymous_client).json()["token"]
    body, signature = token.split(".")
    forged = body + "." + ("A" if signature[0] != "A" else "B") + signature[1:]
    for bad in (forged, "not-a-token", "", body):
        assert anonymous_client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad}"}).status_code == 401


def test_logout_revokes_the_token(anonymous_client):
    token = login(anonymous_client).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert anonymous_client.post("/api/auth/logout", headers=headers).status_code == 200
    assert anonymous_client.get("/api/auth/me", headers=headers).status_code == 401


def test_expired_token_rejected(anonymous_client, monkeypatch):
    monkeypatch.setattr(get_settings(), "SESSION_TTL_HOURS", -1)
    token = login(anonymous_client).json()["token"]
    assert anonymous_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_login_attempts_are_rate_limited(anonymous_client, monkeypatch):
    monkeypatch.setattr(get_settings(), "RATE_LIMIT_LOGIN", "3/minute")
    codes = [login(anonymous_client, TEST_USER, "wrong").status_code for _ in range(4)]
    assert codes[-1] == 429
    assert login(anonymous_client).headers.get("retry-after")


def test_unconfigured_login_fails_closed(anonymous_client, monkeypatch):
    monkeypatch.setattr(get_settings(), "SESSION_SECRET", "")
    assert login(anonymous_client).status_code == 503
    assert anonymous_client.post("/api/chat", json={"message": "hi"}).status_code == 503


def test_password_is_stored_only_as_a_salted_hash():
    first, second = auth.hash_password("same"), auth.hash_password("same")
    assert first != second and first.startswith("pbkdf2_sha256$")
    assert auth.verify_password("same", first) and not auth.verify_password("other", first)
