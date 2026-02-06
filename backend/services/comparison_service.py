"""
Service for comparing two sessions by timestamp.
This file aligns frames by timestamp and outputs structured deltas so you can see exactly how two welding sessions differ frame-by-frame, including thermal, electrical, and mechanical metrics.
"""

from typing import Dict, List, Optional

from models.comparison import FrameDelta, ThermalDelta, TemperatureDelta
from models.frame import Frame
from models.session import Session


def _index_frames_by_timestamp(frames: List[Frame]) -> Dict[int, Frame]:
    return {frame.timestamp_ms: frame for frame in frames}


def _temperature_deltas(frame_a: Frame, frame_b: Frame) -> List[ThermalDelta]:
    if not frame_a.has_thermal_data or not frame_b.has_thermal_data:
        return []
    if not frame_a.thermal_snapshots or not frame_b.thermal_snapshots:
        return []

    deltas: List[ThermalDelta] = []
    b_snapshots_by_distance = {snap.distance_mm: snap for snap in frame_b.thermal_snapshots}

    for snapshot_a in frame_a.thermal_snapshots:
        snapshot_b = b_snapshots_by_distance.get(snapshot_a.distance_mm)
        if snapshot_b is None:
            continue
        b_readings_by_direction = {reading.direction: reading for reading in snapshot_b.readings}
        temp_deltas: List[TemperatureDelta] = []
        for reading_a in snapshot_a.readings:
            reading_b = b_readings_by_direction.get(reading_a.direction)
            if reading_b is None:
                continue
            temp_deltas.append(
                TemperatureDelta(
                    direction=reading_a.direction,
                    delta_temp_celsius=reading_a.temp_celsius - reading_b.temp_celsius,
                )
            )
        deltas.append(
            ThermalDelta(
                distance_mm=snapshot_a.distance_mm,
                readings=temp_deltas,
            )
        )
    return deltas


def _delta_optional(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None:
        return None
    return a - b


def compare_sessions(session_a: Session, session_b: Session) -> List[FrameDelta]:
    """Compare two sessions by aligning frames on timestamp only."""
    frames_a = _index_frames_by_timestamp(session_a.frames)
    frames_b = _index_frames_by_timestamp(session_b.frames)

    shared_timestamps = sorted(set(frames_a.keys()) & set(frames_b.keys()))
    deltas: List[FrameDelta] = []

    for timestamp in shared_timestamps:
        frame_a = frames_a[timestamp]
        frame_b = frames_b[timestamp]
        deltas.append(
            FrameDelta(
                timestamp_ms=timestamp,
                amps_delta=_delta_optional(frame_a.amps, frame_b.amps),
                volts_delta=_delta_optional(frame_a.volts, frame_b.volts),
                angle_degrees_delta=_delta_optional(frame_a.angle_degrees, frame_b.angle_degrees),
                heat_dissipation_rate_celsius_per_sec_delta=_delta_optional(
                    frame_a.heat_dissipation_rate_celsius_per_sec,
                    frame_b.heat_dissipation_rate_celsius_per_sec,
                ),
                thermal_deltas=_temperature_deltas(frame_a, frame_b),
            )
        )
    return deltas
