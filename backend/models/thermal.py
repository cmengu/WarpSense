"""
Thermal sensor models for canonical time-series contract.
Every thermal frame MUST look like this, or the system rejects it
Only data that is already mapped to this shape is allowed to enter — everything else is rejected immediately.
Sensor chaos
   ↓
Sensor-specific model
   ↓
Adapter logic (your code)
   ↓
ThermalSnapshot (strict gatekeeper) <- this is the file
Right now, 5 readings → cardinal directions → same distance
"""

from typing import List, Literal

from pydantic import BaseModel, Field, field_validator


class TemperaturePoint(BaseModel):
    """Single temperature reading at a named direction."""

    direction: Literal["center", "north", "south", "east", "west"] = Field(
        ...,
        description="Direction of the temperature reading (center + 4 cardinal).",
    )
    temp_celsius: float = Field(
        ...,
        description="Temperature in Celsius at the specified direction.",
    )


class ThermalSnapshot(BaseModel):
    """Thermal readings at a fixed distance for one frame."""

    distance_mm: float = Field(
        ...,
        description="Distance along weld in millimeters for this snapshot.",
    )
    readings: List[TemperaturePoint] = Field(
        ...,
        description="Exactly 5 readings: center + 4 cardinal directions.",
        min_length=5,
        max_length=5,
    )

    @field_validator("readings")
    @classmethod
    def validate_readings_count(cls, value: List[TemperaturePoint]) -> List[TemperaturePoint]:
        if len(value) != 5:
            raise ValueError("ThermalSnapshot must contain exactly 5 readings")
        return value
