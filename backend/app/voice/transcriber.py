"""
Speech-to-text with faster-whisper (CTranslate2, int8 on CPU) — Tamil and English, auto-detected.

Lazy: the model loads on the first voice request and stays cached. It needs ~1 GB RAM for "small",
so it is disabled on small servers (VOICE_ENABLED=false) and the endpoint reports that honestly.
"""
import logging
import os
import tempfile
import threading
from dataclasses import dataclass

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

EXTENSIONS = {"audio/webm": ".webm", "audio/ogg": ".ogg", "audio/mp4": ".m4a", "audio/wav": ".wav", "audio/mpeg": ".mp3"}

_lock = threading.Lock()
_model = None


class VoiceUnavailable(RuntimeError):
    pass


class AudioRejected(ValueError):
    pass


@dataclass
class Transcript:
    text: str
    whisper_language: str
    language_probability: float
    duration: float


def is_installed() -> bool:
    try:
        import faster_whisper  # noqa: F401

        return True
    except ImportError:
        return False


def _load():
    global _model
    settings = get_settings()
    if not settings.VOICE_ENABLED:
        raise VoiceUnavailable("voice is disabled on this server")
    if _model is None:
        with _lock:
            if _model is None:
                try:
                    from faster_whisper import WhisperModel
                except ImportError as error:
                    raise VoiceUnavailable("faster-whisper is not installed") from error
                logger.info("Loading Whisper model '%s' (int8, CPU)", settings.VOICE_MODEL_SIZE)
                _model = WhisperModel(settings.VOICE_MODEL_SIZE, device="cpu", compute_type="int8", cpu_threads=4)
    return _model


def transcribe(data: bytes, mime: str) -> Transcript:
    model = _load()
    settings = get_settings()
    # Random temp name + fixed extension: the uploaded filename is never used on disk.
    fd, path = tempfile.mkstemp(suffix=EXTENSIONS[mime], prefix="fa-voice-")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        from faster_whisper import decode_audio

        try:
            audio = decode_audio(path)  # 16 kHz mono float32 (PyAV); raises on corrupt/unsupported audio
        except Exception as error:
            raise AudioRejected("This recording could not be read.") from error
        duration = len(audio) / 16000
        if duration > settings.MAX_AUDIO_SECONDS + 1:
            raise AudioRejected(f"Recordings can be at most {settings.MAX_AUDIO_SECONDS} seconds.")

        # Farmers speak Tamil or English (Tanglish is spoken Tamil). Whisper's open detection often
        # mistakes Tamil for Malayalam/Hindi, so choose between the two supported languages only.
        _, _, all_probabilities = model.detect_language(audio)
        scores = dict(all_probabilities)
        language = "ta" if scores.get("ta", 0.0) >= scores.get("en", 0.0) else "en"
        segments, _ = model.transcribe(audio, language=language, beam_size=1, vad_filter=True,
                                       condition_on_previous_text=False)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        total = scores.get("ta", 0.0) + scores.get("en", 0.0)
        return Transcript(text, language, float(scores.get(language, 0.0) / total) if total else 0.0, duration)
    finally:
        try:
            os.remove(path)
        except OSError:
            logger.warning("Could not delete temporary audio file")
