"""
Image preprocessing with OpenCV — identical to the evaluation transform used in training
(resize shorter side to 256, centre-crop 224, ImageNet normalisation).
"""
from typing import Optional, Tuple

import numpy as np

IMAGE_SIZE = 224
RESIZE_TO = 256
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
MAX_PIXELS = 40_000_000  # refuse decompression bombs


class InvalidImage(ValueError):
    pass


def decode(data: bytes) -> np.ndarray:
    """Bytes → RGB uint8 array. Raises InvalidImage for anything OpenCV can't decode as an image."""
    import cv2

    buffer = np.frombuffer(data, dtype=np.uint8)
    header = cv2.imdecode(buffer, cv2.IMREAD_REDUCED_COLOR_8)  # cheap size probe
    if header is None:
        raise InvalidImage("The file could not be read as an image.")
    if header.shape[0] * header.shape[1] * 64 > MAX_PIXELS:
        raise InvalidImage("The image is too large.")
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise InvalidImage("The file could not be read as an image.")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def quality_problem(rgb: np.ndarray) -> Optional[str]:
    """Rejects photos that can't be analysed meaningfully (tiny, very dark/bright, very blurry)."""
    import cv2

    h, w = rgb.shape[:2]
    if min(h, w) < 64:
        return "too_small"
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    brightness = float(gray.mean())
    if brightness < 25:
        return "too_dark"
    if brightness > 240:
        return "too_bright"
    small = cv2.resize(gray, (256, 256)) if min(h, w) > 256 else gray
    if cv2.Laplacian(small, cv2.CV_64F).var() < 15:
        return "too_blurry"
    return None


def plant_pixel_share(rgb: np.ndarray) -> float:
    """Share of green/yellow/brown (plant-like) pixels — a cheap check that the photo shows vegetation."""
    import cv2

    hsv = cv2.cvtColor(cv2.resize(rgb, (128, 128)), cv2.COLOR_RGB2HSV)
    hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    plant = (hue >= 10) & (hue <= 95) & (sat >= 40) & (val >= 40)  # OpenCV hue is 0–180
    return float(plant.mean())


def to_tensor(rgb: np.ndarray) -> np.ndarray:
    """RGB uint8 → (1, 3, 224, 224) float32, normalised."""
    import cv2

    h, w = rgb.shape[:2]
    scale = RESIZE_TO / min(h, w)
    resized = cv2.resize(rgb, (max(RESIZE_TO, round(w * scale)), max(RESIZE_TO, round(h * scale))), interpolation=cv2.INTER_AREA)
    rh, rw = resized.shape[:2]
    top, left = (rh - IMAGE_SIZE) // 2, (rw - IMAGE_SIZE) // 2
    crop = resized[top : top + IMAGE_SIZE, left : left + IMAGE_SIZE].astype(np.float32) / 255.0
    return ((crop - MEAN) / STD).transpose(2, 0, 1)[None, ...].astype(np.float32)


def preprocess_crop_image(data: bytes) -> Tuple[np.ndarray, np.ndarray]:
    rgb = decode(data)
    return rgb, to_tensor(rgb)
