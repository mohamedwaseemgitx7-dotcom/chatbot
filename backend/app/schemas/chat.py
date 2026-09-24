"""
Chat Request & Response Schemas
"""
import uuid
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.security.validation import sanitize_input_text

MAX_MESSAGE_LENGTH = 1000  # matches the frontend input limit


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH, description="Farmer input text")
    conversation_id: Optional[str] = Field(None, description="Conversation UUID (the Supabase conversation id)")
    language: Optional[Literal["tamil", "english", "tanglish"]] = Field(
        None, description="Client-side language hint; the server detector has the final say"
    )

    @field_validator("message")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = sanitize_input_text(value)
        if not value:
            raise ValueError("Message must not be empty.")
        return value

    @field_validator("conversation_id")
    @classmethod
    def valid_uuid(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        try:
            return str(uuid.UUID(value))
        except ValueError as error:
            raise ValueError("conversation_id must be a UUID.") from error


class Source(BaseModel):
    title: str
    url: str
    publisher: str
    retrieved_at: Optional[str] = None
    verification_status: Optional[str] = None


class ChatResponse(BaseModel):
    language: str
    intent: str
    confidence: float
    response: str
    status: str
    crop: Optional[str] = None
    sources: List[Source] = []
    conversation_id: Optional[str] = None
