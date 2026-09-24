"""
Upload validation by content, not by name: the file's first bytes decide what it is.
Uploaded files are only ever decoded as images/audio — never executed or written with their original name.
"""
from typing import Optional, Tuple

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/ogg", "audio/mp4", "audio/wav", "audio/mpeg"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def sniff_image(data: bytes) -> Optional[str]:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def sniff_audio(data: bytes) -> Optional[str]:
    if data[:4] == b"\x1a\x45\xdf\xa3":  # EBML (WebM/Matroska) — MediaRecorder in Chrome/Firefox
        return "audio/webm"
    if data[:4] == b"OggS":
        return "audio/ogg"
    if data[4:8] == b"ftyp":  # MP4/M4A — MediaRecorder in Safari
        return "audio/mp4"
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav"
    if data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
        return "audio/mpeg"
    return None


def validate_uploaded_image(filename: str, content_type: str, file_size: int, data: bytes = b"") -> Tuple[bool, str]:
    """(ok, reason). The declared content type and name are ignored in favour of the real content."""
    if file_size == 0:
        return False, "The file is empty."
    if file_size > MAX_IMAGE_SIZE_BYTES:
        return False, "File exceeds maximum size of 5 MB."
    if data and sniff_image(data) is None:
        return False, "Unsupported file format. Use JPEG, PNG, or WEBP."
    return True, ""
