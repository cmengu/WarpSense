"""
Pydantic schemas for session annotation API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from models.shared_enums import AnnotationType


def _safe_annotation_type(value: str) -> AnnotationType:
    """Coerce DB string to AnnotationType. Unknown values fallback to defect_confirmed."""
    try:
        return AnnotationType(value)
    except ValueError:
        return AnnotationType.DEFECT_CONFIRMED


class AnnotationCreate(BaseModel):
    """Request body for POST /sessions/{session_id}/annotations."""

    timestamp_ms: int
    annotation_type: AnnotationType
    note: Optional[str] = Field(None, max_length=2000)
    created_by: Optional[str] = Field(None, max_length=128)

    @field_validator("timestamp_ms")
    @classmethod
    def must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("timestamp_ms must be non-negative")
        return v


class AnnotationResponse(BaseModel):
    """Response model for annotation fetch or create."""

    id: int
    session_id: str
    timestamp_ms: int
    annotation_type: AnnotationType
    note: Optional[str]
    created_by: Optional[str]
    created_at: datetime

    @field_validator("annotation_type", mode="before")
    @classmethod
    def coerce_annotation_type(cls, v: object) -> AnnotationType:
        return _safe_annotation_type(str(v)) if v is not None else AnnotationType.DEFECT_CONFIRMED

    class Config:
        from_attributes = True


class DefectLibraryItem(BaseModel):
    """Cross-session defect entry for the defect library page."""

    id: int
    session_id: str
    timestamp_ms: int
    annotation_type: AnnotationType
    note: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    weld_type: Optional[str] = None  # from session
    operator_id: Optional[str] = None  # from session (anonymisable)

    @field_validator("annotation_type", mode="before")
    @classmethod
    def coerce_annotation_type(cls, v: object) -> AnnotationType:
        return _safe_annotation_type(str(v)) if v is not None else AnnotationType.DEFECT_CONFIRMED

    class Config:
        from_attributes = True
