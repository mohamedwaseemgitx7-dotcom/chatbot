"""
Chat Endpoint Router
"""
import uuid

from fastapi import APIRouter, Request, Response
from starlette.concurrency import run_in_threadpool

from app.config.settings import get_settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.security.auth import CurrentUser
from app.security.rate_limit import limiter
from app.services.chat_service import answer

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(lambda: get_settings().RATE_LIMIT_CHAT)
async def chat_endpoint(request: Request, response: Response, body: ChatRequest, user: dict = CurrentUser):
    """
    Multilingual, agriculture-only chat. Answers come from verified knowledge (with sources) or controlled
    templates — never from free text generation. Unexpected errors are handled by the global handler.
    """
    result = await run_in_threadpool(answer, body.message)
    request.state.log_extra = {"intent": result.intent, "status": result.status, "language": result.language,
                               "timings_ms": result.timings_ms}
    return ChatResponse(
        language=result.language,
        intent=result.intent,
        confidence=result.confidence,
        response=result.response,
        status=result.status,
        crop=result.crop,
        sources=result.sources,
        conversation_id=body.conversation_id or str(uuid.uuid4()),
    )
