"""
Image predictions repository — stores AI output for a photo (a preliminary prediction, not a diagnosis).
"""
from typing import Optional

from app.database.supabase import first_value, get_supabase_client

STATUSES = {"processing", "completed", "failed"}


def save_image_prediction(
    message_id: str,
    image_path: str,
    *,
    crop: Optional[str] = None,
    prediction: Optional[str] = None,
    confidence: Optional[float] = None,
    status: str = "completed",
) -> Optional[str]:
    """Inserts a prediction row and returns its id (None when Supabase isn't configured)."""
    if status not in STATUSES:
        raise ValueError(f"Invalid status: {status}")

    client = get_supabase_client()
    if client is None:
        return None
    row = {
        "message_id": message_id,
        "image_url": image_path,
        "crop": crop,
        "prediction": prediction,
        "confidence": None if confidence is None else min(1.0, max(0.0, float(confidence))),
        "status": status,
    }
    return first_value(client.table("image_predictions").insert(row).execute().data, "id")
