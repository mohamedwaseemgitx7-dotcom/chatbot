from pathlib import Path

from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.config.settings import Settings
from app.main import app

ROOT = Path(__file__).resolve().parents[1]


def test_cors_allows_configured_origin_only(client):
    ok = client.options("/api/chat", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.options("/api/chat", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in bad.headers


def test_wildcard_origin_is_dropped_in_production():
    settings = Settings(ENVIRONMENT="production", ALLOWED_ORIGINS="*,https://farmerassist.vercel.app")
    assert settings.allowed_origins_list == ["https://farmerassist.vercel.app"]


def test_cors_origins_alias_is_accepted(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example,https://b.example/")
    assert Settings().allowed_origins_list == ["https://a.example", "https://b.example"]


def test_unexpected_errors_are_sanitised():
    router = APIRouter()

    @router.get("/api/_boom")
    async def boom():
        raise RuntimeError("secret internal detail C:\\\\path\\\\file.py SUPABASE_SERVICE_ROLE_KEY")

    app.include_router(router)
    try:
        response = TestClient(app, raise_server_exceptions=False).get("/api/_boom")
    finally:
        app.router.routes = [r for r in app.router.routes if getattr(r, "path", "") != "/api/_boom"]
    assert response.status_code == 500
    assert response.json() == {"detail": "Something went wrong. Please try again."}
    assert "secret" not in response.text and "SUPABASE" not in response.text


def test_frontend_source_contains_no_private_keys():
    """Real secret values (not the words themselves — the client checks for them on purpose)."""
    import base64
    import json
    import re

    frontend = ROOT / "frontend" / "src"
    text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in frontend.rglob("*") if p.is_file())
    assert not re.search(r"sb_secret_[A-Za-z0-9_-]{16,}", text), "Supabase secret key in frontend source"
    for token in re.findall(r"eyJ[A-Za-z0-9_-]{10,}\.([A-Za-z0-9_-]{10,})\.[A-Za-z0-9_-]{10,}", text):
        payload = json.loads(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)))
        assert payload.get("role") != "service_role", "service-role JWT in frontend source"
    assert "SUPABASE_SERVICE_ROLE_KEY" not in text and "DATABASE_PASSWORD" not in text


def test_env_files_are_git_ignored():
    import shutil
    import subprocess

    if shutil.which("git") and (ROOT / ".git").exists():
        paths = ["backend/.env", "frontend/.env", ".env.production", "frontend/.env.local", "certs/server.pem", "id.key"]
        ignored = subprocess.run(["git", "check-ignore", *paths], cwd=ROOT, capture_output=True, text=True).stdout.split()
        assert sorted(ignored) == sorted(paths)
        kept = subprocess.run(["git", "check-ignore", "frontend/src/lib/supabase.js", "backend/models/embedding/model.onnx",
                               ".env.example"], cwd=ROOT, capture_output=True, text=True).stdout.split()
        assert kept == [], f"needed files would be ignored: {kept}"
    else:
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in (".env", ".env.*", "*.pem", "*.key"):
            assert pattern in ignore.splitlines()
