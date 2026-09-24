"""
Message repository — persists assistant/user messages from the server side.
"""
from typing import Any, Dict, Optional

from app.database.supabase import first_value, get_supabase_client

SENDERS = {"user", "assistant", "system"}
MESSAGE_TYPES = {"text", "image", "voice", "system"}


def save_message(
    conversation_id: str,
    sender: str,
    message: str,
    *,
    language: Optional[str] = None,
    intent: Optional[str] = None,
    confidence: Optional[float] = None,
    message_type: str = "text",
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Inserts one message and returns its id (None when Supabase isn't configured)."""
    if sender not in SENDERS:
        raise ValueError(f"Invalid sender: {sender}")
    if message_type not in MESSAGE_TYPES:
        raise ValueError(f"Invalid message_type: {message_type}")

    client = get_supabase_client()
    if client is None:
        return None
    row = {
        "conversation_id": conversation_id,
        "sender": sender,
        "message": message,
        "language": language,
        "intent": intent,
        "confidence": None if confidence is None else min(1.0, max(0.0, float(confidence))),
        "message_type": message_type,
        "metadata": metadata or {},
    }
    return first_value(client.table("messages").insert(row).execute().data, "id")
