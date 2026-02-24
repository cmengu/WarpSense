"""
Feature extraction from raw sensor data.

Computes 5 features for scoring: amps_stddev, angle_max_deviation,
north_south_delta_avg, heat_diss_stddev, volts_range.

Plus aluminum features: travel_speed_stddev, cyclogram_area, porosity_event_count.

Uses correct field names from Frame: angle_degrees, amps, has_thermal_data.
NOT torch_angle_degrees or frame_type (deprecated).
"""

import math
import statistics
from typing import List, Dict, Any

import numpy as np

from models.session import Session

# Porosity window voltage σ threshold — calibrated via Step 8 (30-session calibration).
# Source: Step 8 output confirmed 0.8 separates expert/novice voltage variance windows.
# To recalibrate: re-run Step 8 and update this value before running Migration B.
POROSITY_SIGMA_THRESHOLD = 0.8


def _compute_cyclogram_area(volts: list, amps: list) -> float:
    """Ellipse area of V-I scatter. Expert: small. Novice: large. π×σ_v×σ_a×sqrt(1-r²)"""
    if len(volts) < 10 or len(amps) < 10:
        return 0.0
    v_std = float(np.std(volts))
    a_std = float(np.std(amps))
    if v_std == 0.0 or a_std == 0.0:
        return 0.0
    r_val = float(np.corrcoef(volts, amps)[0, 1])
    r = 0.0 if (math.isnan(r_val) or abs(r_val) > 1.0) else r_val
    return round(math.pi * v_std * a_std * math.sqrt(max(0.0, 1.0 - r ** 2)), 4)


def extract_features(
    session: Session, angle_target_deg: float = 45
) -> Dict[str, Any]:
    """
    Extract 5 features from a welding session for scoring.

    Field names must match Frame model: f.amps, f.angle_degrees,
    f.has_thermal_data. Wrong names → zeros → scoring broken.

    Args:
        session: Session with raw sensor data (frames with amps, angle_degrees,
                 thermal_snapshots, heat_dissipation_rate_celsius_per_sec, volts)

    Returns:
        Dict with keys: amps_stddev, angle_max_deviation, north_south_delta_avg,
        heat_diss_stddev, volts_range. All floats; empty lists yield 0.
    """
    amps = [f.amps for f in session.frames if f.amps is not None]
    angles = [f.angle_degrees for f in session.frames if f.angle_degrees is not None]
    thermal_frames = [f for f in session.frames if f.has_thermal_data]

    north_temps: List[float] = []
    south_temps: List[float] = []
    for f in thermal_frames:
        for snap in f.thermal_snapshots:
            for r in snap.readings:
                if r.direction == "north":
                    north_temps.append(r.temp_celsius)
                elif r.direction == "south":
                    south_temps.append(r.temp_celsius)

    heat_diss = [
        f.heat_dissipation_rate_celsius_per_sec
        for f in session.frames
        if f.heat_dissipation_rate_celsius_per_sec is not None
    ]
    volts = [f.volts for f in session.frames if f.volts is not None]

    amps_stddev = statistics.stdev(amps) if len(amps) > 1 else 0.0
    angle_max_deviation = (
        max(abs(a - angle_target_deg) for a in angles) if angles else 0.0
    )
    north_south_delta_avg = (
        abs(statistics.mean(north_temps) - statistics.mean(south_temps))
        if north_temps and south_temps
        else 0.0
    )
    heat_diss_stddev = statistics.stdev(heat_diss) if len(heat_diss) > 1 else 0.0
    volts_range = max(volts) - min(volts) if volts else 0.0

    # Travel speed stddev
    travel_speeds = [
        f.travel_speed_mm_per_min for f in session.frames
        if f.travel_speed_mm_per_min is not None
    ]
    travel_speed_stddev = float(np.std(travel_speeds)) if len(travel_speeds) > 1 else 0.0

    # Cyclogram area — arc-on frames only
    arc_frames = [f for f in session.frames if f.volts and f.volts > 1.0 and f.amps]
    cyclogram_area = _compute_cyclogram_area(
        [f.volts for f in arc_frames],
        [f.amps for f in arc_frames],
    )

    # Porosity event count — rolling 30-frame windows; threshold from Step 8 calibration
    porosity_event_count = 0
    window_size = 30
    if len(arc_frames) >= window_size:
        for idx in range(0, len(arc_frames) - window_size, window_size):
            w = [f.volts for f in arc_frames[idx : idx + window_size] if f.volts]
            if len(w) >= window_size // 2 and float(np.std(w)) > POROSITY_SIGMA_THRESHOLD:
                porosity_event_count += 1

    return {
        "amps_stddev": amps_stddev,
        "angle_max_deviation": angle_max_deviation,
        "north_south_delta_avg": north_south_delta_avg,
        "heat_diss_stddev": heat_diss_stddev,
        "volts_range": volts_range,
        "travel_speed_stddev": travel_speed_stddev,
        "cyclogram_area": cyclogram_area,
        "porosity_event_count": porosity_event_count,
    }


def extract_pressure_features(
    sensor_readings: List[Dict[str, Any]],
) -> Dict[str, float]:
    """
    Extract pressure-related features from sensor readings.

    NOT IMPLEMENTED: Intentionally unimplemented for MVP.
    The 5 active scoring features are in extract_features() above.
    Implement when pressure sensors are added to the pipeline.

    Args:
        sensor_readings: List of raw sensor reading dictionaries

    Returns:
        Dictionary with pressure features (avg, variance, etc.)
    """
    return {}


def extract_temperature_features(
    sensor_readings: List[Dict[str, Any]],
) -> Dict[str, float]:
    """
    Extract temperature-related features from sensor readings.

    NOT IMPLEMENTED: Intentionally unimplemented for MVP.
    Thermal metrics are handled via thermal_snapshots in extract_features().
    Implement when additional temperature aggregates are needed.

    Args:
        sensor_readings: List of raw sensor reading dictionaries

    Returns:
        Dictionary with temperature features (avg, stability, etc.)
    """
    return {}


def extract_torch_angle_features(
    sensor_readings: List[Dict[str, Any]],
) -> Dict[str, float]:
    """
    Extract torch angle-related features from sensor readings.

    NOT IMPLEMENTED: Intentionally unimplemented for MVP.
    angle_max_deviation is already computed in extract_features() from
    angle_degrees. Implement when additional angle aggregates are needed.

    Args:
        sensor_readings: List of raw sensor reading dictionaries

    Returns:
        Dictionary with torch angle features (consistency, etc.)
    """
    return {}
