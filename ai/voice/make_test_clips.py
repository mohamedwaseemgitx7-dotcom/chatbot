"""
Generates SYNTHETIC voice test clips (Microsoft neural TTS via edge-tts) for ASR evaluation.

    ai/.venv-train/Scripts/python ai/voice/make_test_clips.py    → data/voice_test/*.mp3 / *.wav

These are text-to-speech recordings, not real farmers: they check that the pipeline works end to end
(upload → Whisper → transcript → chat). Real accuracy on farmers' speech must be measured with real
recordings (datasets/voice/voice_queries.csv lists the prompts to record).
"""
import asyncio
import io
import json
import wave
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[2] / "data" / "voice_test"

CLIPS = [
    ("english_pest", "en-IN-PrabhatNeural", "How can I control stem borer in my paddy field?"),
    ("english_short", "en-IN-NeerjaNeural", "Tomato leaf curl."),
    ("tamil_yellow_leaf", "ta-IN-PallaviNeural", "என் நெல் இலைகள் மஞ்சளாக மாறுகின்றன. என்ன செய்ய வேண்டும்?"),
    ("tamil_fertilizer", "ta-IN-ValluvarNeural", "நெல்லுக்கு எந்த உரம் போட வேண்டும்?"),
    # Tanglish is spoken Tamil: "nel la poochi iruku enna panrathu" said aloud.
    ("tanglish_spoken_pest", "ta-IN-ValluvarNeural", "நெல்லுல பூச்சி இருக்கு, என்ன பண்றது?"),
    ("english_long", "en-IN-PrabhatNeural",
     "Good morning. I am a farmer from Thanjavur. For the last two weeks the leaves of my paddy crop are turning yellow "
     "from the tips, and some plants have small brown spots. I applied urea one month ago. The field has standing water. "
     "Please tell me what could be the problem and what I should do now."),
]


async def synthesize(voice: str, text: str) -> bytes:
    import edge_tts

    audio = b""
    async for chunk in edge_tts.Communicate(text, voice).stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
    return audio


def add_noise(mp3: bytes, snr_db: float) -> bytes:
    """Decodes with PyAV, mixes in white noise at the given SNR, returns 16 kHz mono WAV."""
    import av

    container = av.open(io.BytesIO(mp3))
    resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
    samples = np.concatenate([f.to_ndarray().flatten() for frame in container.decode(audio=0) for f in resampler.resample(frame)])
    signal = samples.astype(np.float32)
    noise = np.random.default_rng(0).normal(0, 1, signal.shape).astype(np.float32)
    noise *= np.sqrt((signal ** 2).mean() / (10 ** (snr_db / 10)) / (noise ** 2).mean())
    mixed = np.clip(signal + noise, -32768, 32767).astype(np.int16)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(16000), w.writeframes(mixed.tobytes())
    return buffer.getvalue()


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, voice, text in CLIPS:
        data = await synthesize(voice, text)
        (OUT / f"{name}.mp3").write_bytes(data)
        manifest.append({"file": f"{name}.mp3", "voice": voice, "expected_text": text, "synthetic": True})
    noisy = add_noise((OUT / "tamil_yellow_leaf.mp3").read_bytes(), snr_db=10)
    (OUT / "tamil_yellow_leaf_noisy_10db.wav").write_bytes(noisy)
    manifest.append({"file": "tamil_yellow_leaf_noisy_10db.wav", "expected_text": CLIPS[2][2], "synthetic": True, "noise": "white, 10 dB SNR"})
    (OUT / "invalid_audio.webm").write_bytes(b"\x1a\x45\xdf\xa3" + np.random.default_rng(1).bytes(4000))
    manifest.append({"file": "invalid_audio.webm", "expected_text": None, "note": "WebM header + random bytes"})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(manifest)} clips → {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
