"""
Feature extraction from raw sensor data.

Computes 5 features for scoring: amps_stddev, angle_max_deviation,
north_south_delta_avg, heat_diss_stddev, volts_range.

Uses correct field names from Frame: angle_degrees, amps, has_thermal_data.
NOT torch_angle_degrees or frame_type (deprecated).
"""

import statistics
from typing import List, Dict, Any

from models.session import Session


def extract_features(session: Session) -> Dict[str, Any]:
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
        max(abs(a - 45) for a in angles) if angles else 0.0
    )
    north_south_delta_avg = (
        abs(statistics.mean(north_temps) - statistics.mean(south_temps))
        if north_temps and south_temps
        else 0.0
    )
    heat_diss_stddev = statistics.stdev(heat_diss) if len(heat_diss) > 1 else 0.0
    volts_range = max(volts) - min(volts) if volts else 0.0

    return {
        "amps_stddev": amps_stddev,
        "angle_max_deviation": angle_max_deviation,
        "north_south_delta_avg": north_south_delta_avg,
        "heat_diss_stddev": heat_diss_stddev,
        "volts_range": volts_range,
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
