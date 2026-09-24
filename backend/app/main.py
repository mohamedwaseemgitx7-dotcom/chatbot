"""
FarmerAssist FastAPI Application
"""
import json
import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.routes import auth, chat, health, image, voice
from app.config.settings import get_settings
from app.security.rate_limit import limiter, rate_limit_exceeded_handler

settings = get_settings()
logging.basicConfig(level=settings.LOG_LEVEL.upper(), format="%(message)s")
logger = logging.getLogger("farmerassist")

app = FastAPI(
    title="FarmerAssist API",
    description="Multilingual agriculture assistant API (English, Tamil, Tanglish)",
    version="1.0.0",
    # Interactive docs only outside production.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,  # the API uses no cookies
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Retry-After", "X-Request-ID"],  # the UI shows a countdown after HTTP 429
    max_age=600,
)


@app.middleware("http")
async def request_log(request: Request, call_next):
    """One structured log line per request. Never logs bodies, headers, keys or uploaded files."""
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if not request.url.path.startswith(("/docs", "/openapi.json", "/redoc")):
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if request.url.path.startswith("/api/auth"):
            response.headers["Cache-Control"] = "no-store"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
    finally:
        entry = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": status,
            "ms": round((time.perf_counter() - started) * 1000, 1),
        }
        entry.update(getattr(request.state, "log_extra", {}) or {})
        logger.info(json.dumps(entry, ensure_ascii=False))


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # Field names and plain reasons only — no echo of the submitted values.
    problems = [{"field": ".".join(str(p) for p in e.get("loc", [])[1:]), "reason": e.get("msg", "invalid")} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "Invalid request.", "errors": problems})


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=getattr(exc, "headers", None))


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    request.state.log_extra = {"error_category": type(exc).__name__}
    logger.exception("Unhandled error (request_id=%s)", getattr(request.state, "request_id", "-"))
    return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})


app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(image.router, prefix="/api", tags=["Image Analysis"])
app.include_router(voice.router, prefix="/api", tags=["Voice Transcription"])


@app.get("/")
async def root():
    return {"name": "FarmerAssist API", "status": "online", "health": "/api/health"}
