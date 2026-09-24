"""
Common Pydantic Schemas
"""
from pydantic import BaseModel
from typing import Optional, Any


class APIResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
