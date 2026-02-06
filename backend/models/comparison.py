"""
Comparison models for session-to-session deltas.
FrameDelta is a structured container for deltas — it doesn’t calculate anything itself; your comparison code fills it with the differences.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class TemperatureDelta(BaseModel):
    """Delta between two temperature readings at a direction."""

    direction: str = Field(..., description="Thermal direction label.")
    delta_temp_celsius: float = Field(
        ...,
        description="Temperature delta in Celsius (session_a - session_b).",
    )


class ThermalDelta(BaseModel):
    """Delta between two thermal snapshots at a fixed distance."""

    distance_mm: float = Field(
        ...,
        description="Distance along weld in millimeters for this snapshot.",
    )
    readings: List[TemperatureDelta] = Field(
        default_factory=list,
        description="Per-direction temperature deltas.",
    )


class FrameDelta(BaseModel):
    """Delta between two frames aligned by timestamp."""

    timestamp_ms: int = Field(
        ...,
        description="Timestamp in milliseconds since session start.",
        ge=0,
    )
    amps_delta: Optional[float] = Field(
        None,
        description="Current delta in amps (session_a - session_b).",
    )
    volts_delta: Optional[float] = Field(
        None,
        description="Voltage delta in volts (session_a - session_b).",
    )
    angle_degrees_delta: Optional[float] = Field(
        None,
        description="Angle delta in degrees (session_a - session_b).",
    )
    heat_dissipation_rate_celsius_per_sec_delta: Optional[float] = Field(
        None,
        description="Heat dissipation delta in °C/sec (session_a - session_b).",
    )
    thermal_deltas: List[ThermalDelta] = Field(
        default_factory=list,
        description="Thermal deltas for this frame.",
    )
