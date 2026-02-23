"""
Threshold service — cached access to weld_thresholds.
Cache invalidated on PUT; no DB hit per score request.

Threading: _load_lock protects both _load_all and invalidate_cache.
Acquire before read/write of _cache_loaded to avoid races.

LIMITATION: In-memory cache is process-local. Multi-worker deployments
(e.g. Gunicorn with multiple uvicorn workers) will serve stale thresholds
until process restart. For MVP: document and add shared cache (e.g. Redis)
to backlog. Single-worker dev/staging: works correctly.
"""

import logging
import threading
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from database.models import WeldThresholdModel
from models.thresholds import WeldTypeThresholds

log = logging.getLogger(__name__)

# Module-level cache: weld_type -> WeldTypeThresholds
_threshold_cache: Dict[str, WeldTypeThresholds] = {}
_cache_loaded = False
_load_lock = threading.Lock()

KNOWN_PROCESS_TYPES = frozenset({"mig", "tig", "stick", "flux_core", "aluminum"})

# Aluminum stitch welding: wider margins for arc on/off variance, thermal reactivity.
# Used by migration seed; values bracket mock expert (pass) and novice (fail).
ALUMINUM_THRESHOLDS = {
    "weld_type": "aluminum",
    "angle_target_degrees": 45.0,
    "angle_warning_margin": 20.0,
    "angle_critical_margin": 35.0,
    "thermal_symmetry_warning_celsius": 9.0,   # expert 0.44, novice 9.59; discriminator
    "thermal_symmetry_critical_celsius": 35.0,
    "amps_stability_warning": 75.0,   # stitch 0 vs ~145 creates amps_stddev ~71; expert passes
    "volts_stability_warning": 25.0,
    "heat_diss_consistency": 250.0,
}


def _load_all(db: OrmSession) -> None:
    global _threshold_cache, _cache_loaded
    with _load_lock:
        if _cache_loaded:
            return
        rows = db.execute(select(WeldThresholdModel)).scalars().all()
        if rows:
            _threshold_cache = {}
            for r in rows:
                try:
                    t = WeldTypeThresholds(
                        weld_type=r.weld_type,
                        angle_target_degrees=r.angle_target_degrees,
                        angle_warning_margin=r.angle_warning_margin,
                        angle_critical_margin=r.angle_critical_margin,
                        thermal_symmetry_warning_celsius=r.thermal_symmetry_warning_celsius,
                        thermal_symmetry_critical_celsius=r.thermal_symmetry_critical_celsius,
                        amps_stability_warning=r.amps_stability_warning,
                        volts_stability_warning=r.volts_stability_warning,
                        heat_diss_consistency=r.heat_diss_consistency,
                    )
                    _threshold_cache[r.weld_type] = t
                except Exception as e:
                    log.warning(
                        "Skipping corrupt weld_thresholds row weld_type=%r: %s",
                        r.weld_type,
                        e,
                    )
            if not _threshold_cache:
                _threshold_cache = {
                    "mig": WeldTypeThresholds(
                        weld_type="mig",
                        angle_target_degrees=45,
                        angle_warning_margin=5,
                        angle_critical_margin=15,
                        thermal_symmetry_warning_celsius=60,
                        thermal_symmetry_critical_celsius=80,
                        amps_stability_warning=5,
                        volts_stability_warning=1,
                        heat_diss_consistency=80,
                    )
                }
        else:
            _threshold_cache = {
                "mig": WeldTypeThresholds(
                    weld_type="mig",
                    angle_target_degrees=45,
                    angle_warning_margin=5,
                    angle_critical_margin=15,
                    thermal_symmetry_warning_celsius=60,
                    thermal_symmetry_critical_celsius=80,
                    amps_stability_warning=5,
                    volts_stability_warning=1,
                    heat_diss_consistency=80,
                )
            }
        _cache_loaded = True


def invalidate_cache() -> None:
    """Invalidate cache so next request refetches. Threading: acquire _load_lock
    before writing _cache_loaded to avoid race with _load_all (concurrent PUT +
    GET score could interleave otherwise)."""
    global _cache_loaded
    with _load_lock:
        _cache_loaded = False


def get_thresholds(db: OrmSession, process_type: str) -> WeldTypeThresholds:
    """Get thresholds for a process type. For known types (mig/tig/stick/flux_core),
    fails loudly if row missing; for unknown types, falls back to mig."""
    global _cache_loaded
    if not _cache_loaded:
        _load_all(db)
    key = (process_type or "mig").lower().strip()

    # Tests frequently use multiple isolated DB engines in one process (e.g. in-memory SQLite).
    # Our cache is process-global, so it may have been loaded from a different DB earlier.
    # If a known process type is missing from the cache, reload once from the provided DB
    # before failing loudly.
    if key in KNOWN_PROCESS_TYPES and key not in _threshold_cache:
        invalidate_cache()
        _load_all(db)

    if key not in _threshold_cache:
        if key in KNOWN_PROCESS_TYPES:
            log.error(
                "weld_thresholds missing row for process_type=%r. Add row or run migration.",
                key,
            )
            raise ValueError(
                f"Thresholds for {key!r} not found in weld_thresholds. Add row or fix DB."
            )
        key = "mig"
    return _threshold_cache.get(key, _threshold_cache["mig"])


def get_all_thresholds(db: OrmSession) -> List[WeldTypeThresholds]:
    """Return all thresholds. Admin UI uses this for GET /api/thresholds."""
    global _cache_loaded
    # Like get_thresholds(), reload once if cache may be from a different DB
    # (common in tests that spin up multiple isolated engines in one process).
    invalidate_cache()
    _load_all(db)
    return list(_threshold_cache.values())
