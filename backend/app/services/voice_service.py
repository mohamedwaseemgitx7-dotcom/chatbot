"""
Voice pipeline: audio → content check → Whisper → transcript → language detection (Tamil/English/Tanglish).
The transcript is returned to the client, which sends it through the normal chat pipeline.
CPU-bound; call it from a threadpool.
"""
from typing import Any, Dict

from app.config.settings import get_settings
from app.nlp.language_detector import detect_language, response_language
from app.security.file_security import sniff_audio
from app.voice.transcriber import AudioRejected, transcribe


def process_voice_audio(data: bytes) -> Dict[str, Any]:
    settings = get_settings()
    if len(data) > settings.MAX_AUDIO_BYTES:
        raise AudioRejected("This recording is too large.")
    if len(data) < 1000:
        raise AudioRejected("This recording is too short.")
    mime = sniff_audio(data)
    if mime is None:
        raise AudioRejected("Unsupported audio format.")
    result = transcribe(data, mime)
    language = response_language(detect_language(result.text)) if result.text else None
    return {
        "text": result.text,
        "detected_language": language,
        "whisper_language": result.whisper_language,
        "language_probability": round(result.language_probability, 3),
        "duration_seconds": round(result.duration, 1),
    }
