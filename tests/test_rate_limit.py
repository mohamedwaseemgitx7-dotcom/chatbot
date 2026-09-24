from app.config.settings import get_settings


def test_chat_rate_limit_returns_clean_429(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "RATE_LIMIT_CHAT", "3/minute")
    codes = [client.post("/api/chat", json={"message": "hi"}).status_code for _ in range(4)]
    assert codes[:3] == [200, 200, 200]
    assert codes[3] == 429
    response = client.post("/api/chat", json={"message": "hi"})
    assert response.json() == {"detail": "Too many requests. Please wait a moment and try again."}
    assert response.headers.get("retry-after")


def test_forwarded_ip_is_ignored_unless_proxy_trusted(client, monkeypatch):
    """Without TRUST_PROXY_HEADERS a client can't dodge the limit by faking X-Forwarded-For."""
    monkeypatch.setattr(get_settings(), "RATE_LIMIT_IMAGE", "2/minute")
    codes = [
        client.post("/api/image/analyze", files={"file": ("x.png", b"not an image", "image/png")},
                    headers={"X-Forwarded-For": f"10.0.0.{i}"}).status_code
        for i in range(3)
    ]
    assert codes[-1] == 429
