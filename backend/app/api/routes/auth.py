"""
Login / session endpoints (single demo account — see app/security/auth.py for the design and its limits).
"""
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.config.settings import get_settings
from app.security import auth
from app.security.rate_limit import limiter

router = APIRouter()


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=256)


@router.post("/auth/login")
@limiter.limit(lambda: get_settings().RATE_LIMIT_LOGIN)
async def login(request: Request, response: Response, body: LoginRequest):
    if not auth.is_configured():
        raise HTTPException(status_code=503, detail="Login is not configured on the server.")
    ok = await run_in_threadpool(auth.check_credentials, body.username, body.password)  # PBKDF2 is CPU-bound
    if not ok:
        request.state.log_extra = {"auth": "failed"}
        raise HTTPException(status_code=401, detail="Incorrect username or password.")
    token, expires = auth.create_token(get_settings().DEMO_USERNAME)
    request.state.log_extra = {"auth": "ok"}
    return {"token": token, "expires_at": expires, "username": get_settings().DEMO_USERNAME}


@router.get("/auth/me")
async def me(claims: dict = auth.CurrentUser):
    return {"username": claims["sub"], "expires_at": claims["exp"]}


@router.post("/auth/logout")
async def logout(claims: dict = auth.CurrentUser):
    auth.revoke(claims)
    return {"status": "logged_out"}
