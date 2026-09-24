"""
Health & Readiness Endpoints — cheap checks only; no model is loaded to answer them.
"""
from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.config.settings import get_settings
from app.database.supabase import check_database
from app.embeddings import embedder
from app.embeddings.vector_store import record_count
from app.nlp import intent_classifier
from app.vision import classifier as vision
from app.voice import transcriber

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "farmerassist-api"}


@router.get("/health/ready")
async def readiness_check():
    database = await run_in_threadpool(check_database)
    knowledge = await run_in_threadpool(record_count)
    settings = get_settings()
    components = {
        "database": database,  # connected | not_configured | unavailable
        "intent_model": "ready" if intent_classifier.is_available() else "missing",
        "embedding_model": "ready" if embedder.is_available() else "missing",
        "knowledge_records": knowledge,
        "vision_model": "ready" if vision.is_available() else "not_trained",
        "voice": ("ready" if transcriber.is_installed() else "not_installed") if settings.VOICE_ENABLED else "disabled",
    }
    chat_ready = components["intent_model"] == "ready" and components["embedding_model"] == "ready"
    return {"status": "ready" if chat_ready and database != "unavailable" else "degraded", **components}
