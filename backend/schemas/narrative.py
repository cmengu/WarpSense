"""
Pydantic schemas for session narrative API.
"""

from datetime import datetime

from pydantic import BaseModel


class NarrativeResponse(BaseModel):
    """Response model for narrative fetch or generation."""

    session_id: str
    narrative_text: str
    model_version: str
    generated_at: datetime
    cached: bool  # True if returned from DB cache

    class Config:
        from_attributes = True


class NarrativeGenerateRequest(BaseModel):
    """Request body for POST /sessions/{session_id}/narrative."""

    force_regenerate: bool = False
