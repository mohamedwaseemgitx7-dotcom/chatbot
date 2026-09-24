"""
Server-side rate limiting (SlowAPI). Limits come from settings: RATE_LIMIT_CHAT / _IMAGE / _VOICE.

Behind a reverse proxy (Render) every request arrives from the proxy's IP, so the client address is read
from X-Forwarded-For — but only when TRUST_PROXY_HEADERS is on, because the header is client-controlled
when there is no proxy in front.
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config.settings import get_settings


def client_ip(request: Request) -> str:
    if get_settings().TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=client_ip, default_limits=["60/minute"], headers_enabled=True)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    response = JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please wait a moment and try again."},
    )
    return request.app.state.limiter._inject_headers(response, request.state.view_rate_limit)
