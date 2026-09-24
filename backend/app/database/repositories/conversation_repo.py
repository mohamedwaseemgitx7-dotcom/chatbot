"""
Conversation repository.

The backend's client bypasses RLS, so ownership must be checked explicitly before acting on a
conversation id that came from a request.
"""
from typing import Optional

from app.database.supabase import get_supabase_client


def conversation_belongs_to(conversation_id: str, user_id: str) -> bool:
    client = get_supabase_client()
    if client is None:
        return False
    rows = (
        client.table("conversations")
        .select("id")
        .eq("id", conversation_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
    )
    return bool(rows)


def get_conversation_owner(conversation_id: str) -> Optional[str]:
    client = get_supabase_client()
    if client is None:
        return None
    rows = client.table("conversations").select("user_id").eq("id", conversation_id).limit(1).execute().data
    return rows[0]["user_id"] if rows else None
