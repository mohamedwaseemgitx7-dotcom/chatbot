"""
Pytest Global Test Fixtures

`backend/` is put on sys.path by `pythonpath = backend` in pytest.ini.
"""
import os

# Generous limits so ordinary tests never trip the rate limiter; test_rate_limit.py lowers them on purpose.
os.environ.setdefault("RATE_LIMIT_CHAT", "1000/minute")
os.environ.setdefault("RATE_LIMIT_IMAGE", "1000/minute")
os.environ.setdefault("RATE_LIMIT_VOICE", "1000/minute")

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)


def png_bytes(width: int = 300, height: int = 300, color=(40, 140, 50), noise: bool = True) -> bytes:
    """A valid PNG in memory (leaf-green with texture by default)."""
    import cv2

    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:] = color[::-1]
    if noise:
        rng = np.random.default_rng(0)
        image = np.clip(image.astype(np.int16) + rng.integers(-40, 40, image.shape), 0, 255).astype(np.uint8)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return encoded.tobytes()


@pytest.fixture
def make_png():
    return png_bytes
