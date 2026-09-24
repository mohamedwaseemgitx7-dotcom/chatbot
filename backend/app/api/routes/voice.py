"""
Voice Speech-to-Text Endpoint Router
"""
from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile
from starlette.concurrency import run_in_threadpool

from app.api.routes.image import read_limited
from app.config.settings import get_settings
from app.security.auth import CurrentUser
from app.security.rate_limit import limiter
from app.services.voice_service import process_voice_audio
from app.voice.transcriber import AudioRejected, VoiceUnavailable

router = APIRouter()


@router.post("/voice/transcribe")
@limiter.limit(lambda: get_settings().RATE_LIMIT_VOICE)
async def transcribe_voice_endpoint(request: Request, response: Response, audio: UploadFile = File(...), user: dict = CurrentUser):
    """
    Transcribes a Tamil/English/Tanglish voice question. Returns 503 when voice is disabled on this server.
    """
    settings = get_settings()
    if not settings.VOICE_ENABLED:
        raise HTTPException(status_code=503, detail="Voice input isn't available on this server.")
    data = await read_limited(audio, settings.MAX_AUDIO_BYTES)
    try:
        result = await run_in_threadpool(process_voice_audio, data)
    except AudioRejected as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except VoiceUnavailable as error:
        raise HTTPException(status_code=503, detail="Voice input isn't available on this server.") from error
    request.state.log_extra = {"voice_language": result["detected_language"], "duration_s": result["duration_seconds"]}
    return result
