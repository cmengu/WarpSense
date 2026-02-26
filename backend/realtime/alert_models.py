"""
Pydantic models for real-time alert engine.
"""

from typing import Optional

from pydantic import BaseModel, Field


class FrameInput(BaseModel):
    """Minimal frame data for alert rules. No angle_degrees (work angle)."""

    frame_index: int = Field(..., description="Loop index for logging and payload.")
    timestamp_ms: Optional[float] = Field(
        None,
        description="Simulated time in ms. If set, AlertEngine uses this for suppression instead of wall clock.",
    )
    travel_angle_degrees: float | None = Field(
        None,
        description="Travel angle (push/drag). Expert ~12°. Rule 2.",
    )
    travel_speed_mm_per_min: float | None = Field(
        None,
        description="Torch travel speed in mm/min. Rule 3.",
    )
    volts: Optional[float] = Field(
        None,
        description="Arc voltage in V. Required for arc_instability, undercut, lack_of_fusion, burn_through.",
    )
    amps: Optional[float] = Field(
        None,
        description="Arc current in A. Required for crater_crack, undercut, lack_of_fusion, burn_through.",
    )
    ns_asymmetry: float = Field(
        0.0,
        description="North minus south temperature at 10mm. Rule 1.",
    )


class AlertPayload(BaseModel):
    """Alert message schema for WebSocket and HTTP POST."""

    frame_index: int
    rule_triggered: str
    severity: str
    message: str
    correction: str
    timestamp_ms: float
