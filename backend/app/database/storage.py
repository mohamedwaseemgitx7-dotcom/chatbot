"""
Supabase Storage uploads (server side).

Files live in private buckets at <user_id>/<conversation_id>/<uuid>.<ext>; original file names are
never used in paths. Buckets also enforce size and MIME limits on their own.
"""
import uuid
from typing import Optional

from app.config.settings import get_settings
from app.database.supabase import get_supabase_client

IMAGE_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def build_object_path(user_id: str, conversation_id: str, content_type: str) -> str:
    extension = IMAGE_EXTENSIONS.get(content_type)
    if extension is None:
        raise ValueError("Unsupported image type.")
    # uuid.UUID() rejects anything that isn't a real id, so a caller can't inject "../" into the path.
    return f"{uuid.UUID(user_id)}/{uuid.UUID(conversation_id)}/{uuid.uuid4()}.{extension}"


def upload_crop_image(image_bytes: bytes, content_type: str, user_id: str, conversation_id: str) -> Optional[str]:
    """Uploads a crop photo and returns its storage path, or None when Supabase isn't configured."""
    client = get_supabase_client()
    if client is None:
        return None
    path = build_object_path(user_id, conversation_id, content_type)
    client.storage.from_(get_settings().STORAGE_BUCKET_NAME).upload(
        path, image_bytes, {"content-type": content_type, "upsert": "false"}
    )
    return path


def signed_image_url(path: str, expires_in: int = 3600) -> Optional[str]:
    """Short-lived URL for a stored photo (the bucket is private)."""
    client = get_supabase_client()
    if client is None:
        return None
    result = client.storage.from_(get_settings().STORAGE_BUCKET_NAME).create_signed_url(path, expires_in)
    return result.get("signedURL") or result.get("signedUrl")
