"""
Image Analysis Schemas
"""
from typing import List, Literal, Optional

from pydantic import BaseModel

from app.schemas.chat import Source


class Alternative(BaseModel):
    crop: str
    condition: str
    confidence: float


class ImageAnalysisResponse(BaseModel):
    status: Literal["ok", "uncertain", "model_unavailable"]
    message: Optional[str] = None
    reason: Optional[str] = None
    crop: Optional[str] = None
    prediction: Optional[str] = None
    healthy: Optional[bool] = None
    confidence: Optional[float] = None
    top_predictions: List[Alternative] = []
    possible_causes: List[str] = []
    recommended_next_steps: List[str] = []
    sources: List[Source] = []
    disclaimer: str
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    dataset_version: Optional[str] = None
