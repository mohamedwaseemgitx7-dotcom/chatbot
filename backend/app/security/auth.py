"""
Single-account demo login (server-side).

The account comes from the backend environment only:
  DEMO_USERNAME        login name
  DEMO_PASSWORD_HASH   pbkdf2_sha256$<iterations>$<salt>$<hash>  — create with scripts/hash_password.py
  SESSION_SECRET       ≥ 32 random characters, signs session tokens
No plaintext password is stored anywhere. Tokens are HMAC-SHA256 signed, expire after SESSION_TTL_HOURS,
and are sent as "Authorization: Bearer <token>". Logout revokes a token until it would have expired.

LIMITATION: this is one shared demo account, not per-farmer accounts. For real multi-user login, move to
Supabase Auth (email/phone OTP) — the frontend already has a per-browser Supabase session for chat history.
If DEMO_USERNAME / DEMO_PASSWORD_HASH / SESSION_SECRET are missing, login fails closed (503), never open.
"""
import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from typing import Optional

from fastapi import Depends, HTTPException, Request

from app.config.settings import get_settings

PBKDF2_ITERATIONS = 600_000
_revoked: dict[str, float] = {}  # token id → expiry (in-memory; a restart forgets revocations, tokens still expire)
_revoked_lock = threading.Lock()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt, expected = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), _unb64(salt), int(iterations))
        return hmac.compare_digest(digest, _unb64(expected))
    except (ValueError, TypeError):
        return False


def is_configured() -> bool:
    s = get_settings()
    return bool(s.DEMO_USERNAME and s.DEMO_PASSWORD_HASH and len(s.SESSION_SECRET) >= 32)


def check_credentials(username: str, password: str) -> bool:
    """Constant-time: the password hash is always computed, even for an unknown username."""
    s = get_settings()
    user_ok = hmac.compare_digest(username.strip().lower().encode(), s.DEMO_USERNAME.strip().lower().encode())
    password_ok = verify_password(password, s.DEMO_PASSWORD_HASH)
    return user_ok and password_ok


def _sign(payload: bytes) -> str:
    return _b64(hmac.new(get_settings().SESSION_SECRET.encode(), payload, hashlib.sha256).digest())


def create_token(username: str) -> tuple[str, int]:
    expires = int(time.time()) + get_settings().SESSION_TTL_HOURS * 3600
    payload = json.dumps({"sub": username, "exp": expires, "jti": secrets.token_hex(8)}, separators=(",", ":")).encode()
    return f"{_b64(payload)}.{_sign(payload)}", expires


def read_token(token: str) -> Optional[dict]:
    try:
        body, signature = token.split(".")
        payload = _unb64(body)
        if not hmac.compare_digest(signature, _sign(payload)):
            return None
        claims = json.loads(payload)
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    if claims.get("exp", 0) < time.time():
        return None
    with _revoked_lock:
        if claims.get("jti") in _revoked:
            return None
    return claims


def revoke(claims: dict) -> None:
    now = time.time()
    with _revoked_lock:
        for jti, exp in list(_revoked.items()):
            if exp < now:
                del _revoked[jti]
        _revoked[claims["jti"]] = claims["exp"]


def bearer_token(request: Request) -> str:
    header = request.headers.get("authorization", "")
    return header[7:].strip() if header.lower().startswith("bearer ") else ""


def require_user(request: Request) -> dict:
    """FastAPI dependency for protected endpoints."""
    if not is_configured():
        raise HTTPException(status_code=503, detail="Login is not configured on the server.")
    claims = read_token(bearer_token(request))
    if claims is None:
        raise HTTPException(status_code=401, detail="Please log in again.", headers={"WWW-Authenticate": "Bearer"})
    request.state.user = claims["sub"]
    return claims


CurrentUser = Depends(require_user)
