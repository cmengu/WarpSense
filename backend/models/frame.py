"""
Frame model for canonical time-series welding data.
Everything we know about the weld at one 10ms instant.
there are some optional data, adapt for next time
Key points of failure:
Welding does require back-and-forth passes, so a strictly increasing distance validator is a simplification for AI/plotting convenience, not a reflection of the true motion.
timestamp should had strictly increasing validator
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, computed_field, field_validator

from .thermal import ThermalSnapshot


def _validate_optional_positive(name: str, value: Optional[float]) -> Optional[float]:
    """Reject negative volts or amps when present."""
    if value is not None and value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}")
    return value


def _validate_angle_degrees(value: Optional[float]) -> Optional[float]:
    """Reject angle outside 0–360 when present."""
    if value is not None and (value < 0 or value > 360):
        raise ValueError(f"angle_degrees must be in [0, 360], got {value}")
    return value


class Frame(BaseModel):
    """Single sensor frame at 100Hz (10ms interval)."""

    timestamp_ms: int = Field(
        ...,
        description="Timestamp in milliseconds since session start.",
        ge=0,
    )
    volts: Optional[float] = Field(
        None,
        description="Voltage in volts, if available for this frame.",
    )
    amps: Optional[float] = Field(
        None,
        description="Current in amps, if available for this frame.",
    )
    angle_degrees: Optional[float] = Field(
        None,
        description="Torch angle in degrees, if available for this frame.",
    )
    thermal_snapshots: List[ThermalSnapshot] = Field(
        default_factory=list,
        description="Thermal snapshots for this frame (may be empty).",
    )
    optional_sensors: Optional[Dict[str, bool]] = Field(
        None,
        description="Optional sensor availability flags for partial frames.",
    )
    heat_dissipation_rate_celsius_per_sec: Optional[float] = Field(
        None,
        description="Heat dissipation rate in °C/sec, if available.",
    )

    @computed_field  # type: ignore[misc]
    @property
    def has_thermal_data(self) -> bool:
        return len(self.thermal_snapshots) > 0

    @field_validator("thermal_snapshots")
    @classmethod
    def validate_snapshot_distances(
        cls, value: List[ThermalSnapshot]
    ) -> List[ThermalSnapshot]:
        if not value:
            return value
        distances = [snapshot.distance_mm for snapshot in value]
        for i in range(1, len(distances)):
            if distances[i] <= distances[i - 1]:
                raise ValueError(
                    "Thermal snapshot distances must be strictly increasing with no duplicates"
                )
        return value

    @field_validator("thermal_snapshots")
    @classmethod
    def validate_center_reading_per_snapshot(
        cls, value: List[ThermalSnapshot]
    ) -> List[ThermalSnapshot]:
        for snapshot in value:
            center_count = sum(
                1 for reading in snapshot.readings if reading.direction == "center"
            )
            if center_count != 1:
                raise ValueError(
                    "Each thermal snapshot must contain exactly one center reading"
                )
        return value

    @field_validator("volts")
    @classmethod
    def validate_volts_non_negative(cls, value: Optional[float]) -> Optional[float]:
        return _validate_optional_positive("volts", value)

    @field_validator("amps")
    @classmethod
    def validate_amps_non_negative(cls, value: Optional[float]) -> Optional[float]:
        return _validate_optional_positive("amps", value)

    @field_validator("angle_degrees")
    @classmethod
    def validate_angle_range(cls, value: Optional[float]) -> Optional[float]:
        return _validate_angle_degrees(value)
