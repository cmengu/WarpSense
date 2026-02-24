"""
Thresholds API — GET all, PUT one.
"""

from fastapi import APIRouter, Depends, HTTPException

from database.connection import SessionLocal
from database.models import WeldThresholdModel
from models.thresholds import WeldTypeThresholds, WeldThresholdUpdate
from services.threshold_service import (
    invalidate_cache,
    get_all_thresholds,
    get_thresholds,
)

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/thresholds")
async def list_thresholds(db=Depends(get_db)):
    """Return all thresholds. Admin uses this to populate forms."""
    items = get_all_thresholds(db)
    return [t.model_dump() for t in items]


@router.put("/thresholds/{weld_type}")
async def update_threshold(
    weld_type: str,
    body: WeldThresholdUpdate,
    db=Depends(get_db),
):
    """Update thresholds for one process type. Invalidates cache."""
    weld_type = weld_type.lower()
    if weld_type not in ("mig", "tig", "stick", "flux_core", "aluminum"):
        raise HTTPException(status_code=422, detail=f"Unknown weld_type: {weld_type}")
    if body.angle_target_degrees == 0:
        raise HTTPException(
            status_code=422,
            detail="angle_target_degrees must be > 0",
        )
    if body.angle_warning_margin > body.angle_critical_margin:
        raise HTTPException(
            status_code=422,
            detail="angle_warning_margin must be <= angle_critical_margin",
        )
    if body.thermal_symmetry_warning_celsius > body.thermal_symmetry_critical_celsius:
        raise HTTPException(
            status_code=422,
            detail="thermal_symmetry_warning must be <= thermal_symmetry_critical",
        )
    # Note: amps/volts/heat_diss have no ordering relationship — validation is asymmetric by design
    row = db.query(WeldThresholdModel).filter_by(weld_type=weld_type).first()
    if not row:
        raise HTTPException(
            status_code=404, detail=f"Thresholds for {weld_type} not found"
        )
    row.angle_target_degrees = body.angle_target_degrees
    row.angle_warning_margin = body.angle_warning_margin
    row.angle_critical_margin = body.angle_critical_margin
    row.thermal_symmetry_warning_celsius = body.thermal_symmetry_warning_celsius
    row.thermal_symmetry_critical_celsius = body.thermal_symmetry_critical_celsius
    row.amps_stability_warning = body.amps_stability_warning
    row.volts_stability_warning = body.volts_stability_warning
    row.heat_diss_consistency = body.heat_diss_consistency
    if body.travel_speed_consistency is not None:
        row.travel_speed_consistency = body.travel_speed_consistency
    if body.cyclogram_area_max is not None:
        row.cyclogram_area_max = body.cyclogram_area_max
    if body.porosity_event_max is not None:
        row.porosity_event_max = body.porosity_event_max
    try:
        db.commit()
    finally:
        invalidate_cache()
    updated = WeldTypeThresholds(
        weld_type=row.weld_type,
        angle_target_degrees=row.angle_target_degrees,
        angle_warning_margin=row.angle_warning_margin,
        angle_critical_margin=row.angle_critical_margin,
        thermal_symmetry_warning_celsius=row.thermal_symmetry_warning_celsius,
        thermal_symmetry_critical_celsius=row.thermal_symmetry_critical_celsius,
        amps_stability_warning=row.amps_stability_warning,
        volts_stability_warning=row.volts_stability_warning,
        heat_diss_consistency=row.heat_diss_consistency,
        travel_speed_consistency=getattr(row, "travel_speed_consistency", None),
        cyclogram_area_max=getattr(row, "cyclogram_area_max", None),
        porosity_event_max=getattr(row, "porosity_event_max", None),
    )
    return updated.model_dump()
