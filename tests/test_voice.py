import os

import pytest

from app.config.settings import get_settings
from app.security.file_security import sniff_audio
from app.voice import transcriber


def upload(client, data, name="voice.webm", mime="audio/webm"):
    return client.post("/api/voice/transcribe", files={"audio": (name, data, mime)})


def test_disabled_voice_returns_503(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "VOICE_ENABLED", False)
    response = upload(client, b"\x1a\x45\xdf\xa3" + b"0" * 2000)
    assert response.status_code == 503
    assert response.json()["detail"] == "Voice input isn't available on this server."


@pytest.mark.parametrize("data", [b"MZ executable" * 200, b"plain text " * 200, b"\x00" * 5000])
def test_invalid_audio_is_rejected(client, monkeypatch, data):
    monkeypatch.setattr(get_settings(), "VOICE_ENABLED", True)
    response = upload(client, data)
    assert response.status_code == 400


def test_oversized_audio_is_rejected(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "VOICE_ENABLED", True)
    assert upload(client, b"\x1a\x45\xdf\xa3" + b"0" * (10 * 1024 * 1024 + 10)).status_code == 413


@pytest.mark.parametrize("header, mime", [
    (b"\x1a\x45\xdf\xa3", "audio/webm"), (b"OggS", "audio/ogg"), (b"\x00\x00\x00\x18ftypM4A ", "audio/mp4"),
    (b"RIFF\x00\x00\x00\x00WAVE", "audio/wav"), (b"ID3", "audio/mpeg"),
])
def test_audio_sniffing(header, mime):
    assert sniff_audio(header + b"\x00" * 64) == mime


VOICE_SAMPLES = os.environ.get("FA_VOICE_SAMPLES")  # folder with generated test clips (see ai/voice/make_test_clips.py)


@pytest.mark.skipif(not (VOICE_SAMPLES and transcriber.is_installed()), reason="set FA_VOICE_SAMPLES to run real Whisper tests")
def test_real_transcription_feeds_chat(client, monkeypatch):
    from pathlib import Path

    monkeypatch.setattr(get_settings(), "VOICE_ENABLED", True)
    assert VOICE_SAMPLES
    clip = next(Path(VOICE_SAMPLES).glob("english_*"))
    body = upload(client, clip.read_bytes(), clip.name, "audio/mpeg").json()
    assert body["text"] and body["detected_language"] == "english"
    reply = client.post("/api/chat", json={"message": body["text"]}).json()
    assert reply["status"] in {"answered", "no_knowledge", "clarification", "guidance"}
