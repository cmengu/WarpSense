"""
Thermal geometry primitives.

Two asymmetry measures exist on purpose — they answer different questions:
  north_south_mean_delta — |mean(all N readings) - mean(all S readings)|
                           across every snapshot of every thermal frame.
                           Session-scale symmetry; the floor's
                           north_south_delta_avg feature.
  nsew_asymmetry         — max(|N-S|, |E-W|) from the FIRST snapshot of one
                           frame, -1.0 sentinel when no thermal data.
                           Instantaneous asymmetry at prediction time; the
                           warp predictor's thermal_asymmetry feature.
"""

from typing import List, Optional

from warpsense.signal.stats import safe_float


def north_south_mean_delta(frames: List) -> float:
    """|mean north - mean south| over all thermal snapshots; 0.0 when either side is empty.

    Frames are pydantic Frame objects; direction match is exact ("north"/"south"),
    preserving the floor extractor's historical behavior.
    """
    north_temps: List[float] = []
    south_temps: List[float] = []
    for f in frames:
        if not f.has_thermal_data:
            continue
        for snap in f.thermal_snapshots:
            for r in snap.readings:
                if r.direction == "north":
                    north_temps.append(r.temp_celsius)
                elif r.direction == "south":
                    south_temps.append(r.temp_celsius)
    if not north_temps or not south_temps:
        return 0.0
    import statistics

    return abs(statistics.mean(north_temps) - statistics.mean(south_temps))


def nsew_asymmetry(frame: dict) -> float:
    """max(|N-S|, |E-W|) from the frame's first thermal snapshot; -1.0 = no thermal data.

    Dict-shaped frames (DB/JSONB path). Direction keys normalized to lowercase
    (DB may return NORTH/north/North); duplicate directions: first occurrence
    wins; missing directions read as 0; non-numeric temps coerce via safe_float.
    """
    snapshots = frame.get("thermal_snapshots") or []
    if not snapshots:
        return -1.0
    readings_list = snapshots[0].get("readings") or []
    readings = {}
    for r in readings_list:
        d = r.get("direction")
        if d is not None:
            key = str(d).lower()
            if key not in readings:
                readings[key] = safe_float(r.get("temp_celsius"), 0.0)
    ns = abs(readings.get("north", 0) - readings.get("south", 0))
    ew = abs(readings.get("east", 0) - readings.get("west", 0))
    return max(ns, ew)


def latest_center_temp(window: List[dict]) -> float:
    """Most recent "center" reading scanning the window backwards; -1.0 when absent.

    Only each frame's first snapshot is consulted, matching nsew_asymmetry.
    """
    temp = -1.0
    for f in reversed(window):
        snapshots = f.get("thermal_snapshots") or []
        if snapshots:
            for r in snapshots[0].get("readings") or []:
                if str(r.get("direction") or "").lower() == "center":
                    temp = safe_float(r.get("temp_celsius"), -1.0)
                    break
        if temp >= 0:
            break
    return temp
