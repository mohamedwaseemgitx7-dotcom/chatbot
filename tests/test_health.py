def test_health_is_cheap_and_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "farmerassist-api"}


def test_readiness_reports_components(client):
    body = client.get("/api/health/ready").json()
    for key in ("database", "intent_model", "embedding_model", "knowledge_records", "vision_model", "voice"):
        assert key in body
    assert body["intent_model"] == "ready"
    assert body["embedding_model"] == "ready"
    assert body["voice"] in {"disabled", "ready", "not_installed"}


def test_request_id_header(client):
    assert client.get("/api/health").headers.get("x-request-id")
