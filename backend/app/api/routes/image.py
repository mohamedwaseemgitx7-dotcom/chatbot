"""
Crop Image Analysis Endpoint Router
"""
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile
from starlette.concurrency import run_in_threadpool

from app.config.settings import get_settings
from app.schemas.image import ImageAnalysisResponse
from app.security.auth import CurrentUser
from app.security.rate_limit import limiter
from app.services.image_service import UnsupportedImage, analyze

router = APIRouter()


async def read_limited(upload: UploadFile, limit: int) -> bytes:
    """Reads at most limit+1 bytes so an oversized upload is rejected without loading it all."""
    data = await upload.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status_code=413, detail="File too large.")
    return data


@router.post("/image/analyze", response_model=ImageAnalysisResponse, response_model_exclude_none=True)
@limiter.limit(lambda: get_settings().RATE_LIMIT_IMAGE)
async def analyze_image_endpoint(
    request: Request,
    response: Response,  # SlowAPI adds X-RateLimit-* headers to it
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None),
    user: dict = CurrentUser,
):
    """
    Preliminary crop-leaf analysis. The photo itself is stored by the client in the user's private
    Supabase Storage folder (RLS-protected); this endpoint only analyses the bytes it receives.
    """
    data = await read_limited(file, get_settings().MAX_IMAGE_BYTES)
    try:
        result = await run_in_threadpool(analyze, data)
    except UnsupportedImage as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    request.state.log_extra = {"image_status": result["status"], "prediction": result.get("prediction")}
    return result
