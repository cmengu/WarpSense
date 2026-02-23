"""
Pydantic models for weld quality thresholds.
One row per process type (mig, tig, stick, flux_core).
"""

from pydantic import BaseModel, Field


class WeldTypeThresholds(BaseModel):
    """Thresholds for one process type. Pass = actual <= threshold."""

    weld_type: str = Field(..., description="Process type: mig|tig|stick|flux_core")
    angle_target_degrees: float = Field(
        ...,
        gt=0,
        le=90,
        description="Must be > 0; 0 makes scoring useless",
    )
    angle_warning_margin: float = Field(..., ge=0, le=45)
    angle_critical_margin: float = Field(..., ge=0, le=45)
    thermal_symmetry_warning_celsius: float = Field(..., ge=0, le=500)
    thermal_symmetry_critical_celsius: float = Field(..., ge=0, le=500)
    amps_stability_warning: float = Field(..., ge=0)
    volts_stability_warning: float = Field(..., ge=0)
    heat_diss_consistency: float = Field(..., ge=0)


class WeldThresholdUpdate(BaseModel):
    """Request body for PUT /api/thresholds/:weld_type."""

    angle_target_degrees: float = Field(..., gt=0, le=90)
    angle_warning_margin: float = Field(..., ge=0, le=45)
    angle_critical_margin: float = Field(..., ge=0, le=45)
    thermal_symmetry_warning_celsius: float = Field(..., ge=0, le=500)
    thermal_symmetry_critical_celsius: float = Field(..., ge=0, le=500)
    amps_stability_warning: float = Field(..., ge=0)
    volts_stability_warning: float = Field(..., ge=0)
    heat_diss_consistency: float = Field(..., ge=0)
