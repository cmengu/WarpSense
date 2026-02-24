"""
Pydantic schemas for certification API responses.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from models.shared_enums import CertificationStatus


class CertStandardResponse(BaseModel):
    """Cert standard metadata for API response."""

    id: str
    name: str
    required_score: float
    sessions_required: int
    weld_type: Optional[str] = None

    class Config:
        from_attributes = True


class CertificationStatusResponse(BaseModel):
    """Per-standard certification status for a welder."""

    cert_standard: CertStandardResponse
    status: CertificationStatus
    evaluated_at: datetime
    qualifying_sessions: int
    sessions_needed: int
    current_avg_score: Optional[float] = None
    sessions_to_target: Optional[int] = None
    qualifying_session_ids: Optional[List[str]] = None

    class Config:
        from_attributes = True


class WelderCertificationSummary(BaseModel):
    """Full certification summary for a welder across all standards."""

    welder_id: str
    certifications: List[CertificationStatusResponse]
