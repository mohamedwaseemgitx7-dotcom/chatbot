"""
Supabase admin client for the backend.

Uses the secret (service-role) key, which BYPASSES Row Level Security. Only use it for server-side
work (persisting AI results, knowledge ingestion, rate-limit logs), always check ownership yourself
(see repositories/conversation_repo.py), and never return this key to the browser.
"""
import logging
from typing import Any, Literal, Optional

from postgrest.types import CountMethod
from supabase import Client, create_client

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None

DatabaseStatus = Literal["connected", "not_configured", "unavailable"]


def is_configured() -> bool:
    settings = get_settings()
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY)


def get_supabase_client() -> Optional[Client]:
    """Returns the shared admin client, or None when Supabase isn't configured."""
    global _supabase_client
    if _supabase_client is None and is_configured():
        settings = get_settings()
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _supabase_client


def check_database() -> DatabaseStatus:
    """Cheap connectivity check (blocking — call it from a threadpool in async code)."""
    client = get_supabase_client()
    if client is None:
        return "not_configured"
    try:
        client.table("knowledge").select("id", count=CountMethod.exact, head=True).execute()
        return "connected"
    except Exception:  # network, auth or schema problem — details go to the log, not the response
        logger.exception("Supabase connectivity check failed")
        return "unavailable"


def first_value(data: Any, key: str) -> Optional[str]:
    """`key` of the first row of a PostgREST result (`.execute().data`) as a string, or None if there is no row."""
    if isinstance(data, list) and data and isinstance(data[0], dict):
        value = data[0].get(key)
        return None if value is None else str(value)
    return None
