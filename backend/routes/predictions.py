"""
Warp risk prediction endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as OrmSession
from pydantic import BaseModel
from typing import Literal

from models.shared_enums import RiskLevel
from routes.sessions import get_db, get_session_frames_raw
from services.prediction_service import predict_warp_risk


router = APIRouter(prefix="/api/sessions", tags=["predictions"])


class WarpRiskResponse(BaseModel):
    session_id: str
    probability: float
    risk_level: Literal["ok", "warning", "critical"]
    model_available: bool
    window_frames_used: int


@router.get("/{session_id}/warp-risk", response_model=WarpRiskResponse)
def get_warp_risk(session_id: str, db: OrmSession = Depends(get_db)):
    """
    Returns warp risk probability for the last 50 frames of a session.
    Degrades gracefully if ONNX model unavailable.
    """
    frames = get_session_frames_raw(session_id, db, limit=50)
    if frames is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    result = predict_warp_risk(frames)
    return WarpRiskResponse(
        session_id=session_id,
        probability=result["probability"],
        risk_level=result["risk_level"].value,
        model_available=result["model_available"],
        window_frames_used=len(frames),
    )
