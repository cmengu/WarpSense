"""
Unit tests for warpsense/signal — the shared signal-truth primitives.

These pin the *semantics* (null handling, sentinels, boundary strictness);
the snapshot suite separately pins that consumers produce identical numbers.
"""

import math

import numpy as np
import pandas as pd
import pytest

from warpsense.signal.arc import (
    ARC_ON_MIN_AMPS,
    ARC_ON_MIN_VOLTS,
    df_arc_mask,
    is_arc_on,
)
from warpsense.signal.stats import (
    mean,
    population_std,
    safe_float,
    sample_std,
    value_range,
)
from warpsense.signal.thermal import (
    latest_center_temp,
    north_south_mean_delta,
    nsew_asymmetry,
)


# ── arc ─────────────────────────────────────────────────────────────────────

def test_arc_on_nominal_weld():
    assert is_arc_on(22.5, 150.0)


def test_arc_off_when_either_missing():
    assert not is_arc_on(None, 150.0)
    assert not is_arc_on(22.5, None)
    assert not is_arc_on(None, None)


def test_arc_boundary_is_strict():
    # Exactly at the floor is OFF — matches the classifier's historical `> 5`.
    assert not is_arc_on(ARC_ON_MIN_VOLTS, 150.0)
    assert not is_arc_on(22.5, ARC_ON_MIN_AMPS)
    assert is_arc_on(ARC_ON_MIN_VOLTS + 1e-9, ARC_ON_MIN_AMPS + 1e-9)


def test_arc_off_during_gap():
    assert not is_arc_on(0.4, 0.0)


def test_df_arc_mask_matches_scalar_including_nan():
    df = pd.DataFrame(
        {
            "volts": [22.5, 0.4, np.nan, 5.0, 6.0],
            "amps": [150.0, 0.0, 150.0, 150.0, np.nan],
        }
    )
    expected = [
        is_arc_on(None if pd.isna(v) else v, None if pd.isna(a) else a)
        for v, a in zip(df["volts"], df["amps"])
    ]
    assert df_arc_mask(df).tolist() == expected == [True, False, False, False, False]


# ── stats ───────────────────────────────────────────────────────────────────

def test_sample_std_is_n_minus_1_and_guarded():
    import statistics

    xs = [1.0, 2.0, 3.0, 4.0]
    assert sample_std(xs) == statistics.stdev(xs)
    assert sample_std([1.0]) == 0.0
    assert sample_std([]) == 0.0


def test_population_std_is_n_and_guarded():
    xs = [1.0, 2.0, 3.0, 4.0]
    assert population_std(xs) == float(np.std(xs))
    assert population_std(xs) != sample_std(xs)  # the two variants must not collapse
    assert population_std([1.0]) == 0.0


def test_mean_default_for_empty():
    assert mean([2.0, 4.0]) == 3.0
    assert mean([], 45.0) == 45.0


def test_value_range():
    assert value_range([21.9, 22.5, 22.1]) == pytest.approx(0.6)
    assert value_range([]) == 0.0


def test_safe_float_coercions():
    assert safe_float("21.5") == 21.5
    assert safe_float(7) == 7.0
    assert safe_float(None, -1.0) == -1.0
    assert safe_float("not-a-number", -1.0) == -1.0
    assert safe_float({"nested": 1}, 0.0) == 0.0


# ── thermal ─────────────────────────────────────────────────────────────────

def _frame_dict(readings, extra_snapshots=0):
    snaps = [{"readings": readings}]
    snaps += [{"readings": [{"direction": "north", "temp_celsius": 999.0}]}] * extra_snapshots
    return {"thermal_snapshots": snaps}


def test_nsew_sentinel_when_no_thermal():
    assert nsew_asymmetry({"thermal_snapshots": []}) == -1.0
    assert nsew_asymmetry({}) == -1.0


def test_nsew_uses_first_snapshot_only():
    frame = _frame_dict(
        [
            {"direction": "north", "temp_celsius": 100.0},
            {"direction": "south", "temp_celsius": 90.0},
        ],
        extra_snapshots=2,  # later snapshots with wild values must be ignored
    )
    assert nsew_asymmetry(frame) == 10.0


def test_nsew_direction_case_and_first_occurrence_wins():
    frame = _frame_dict(
        [
            {"direction": "NORTH", "temp_celsius": 100.0},
            {"direction": "north", "temp_celsius": 55.0},  # duplicate — ignored
            {"direction": "South", "temp_celsius": 80.0},
        ]
    )
    assert nsew_asymmetry(frame) == 20.0


def test_nsew_max_of_both_axes():
    frame = _frame_dict(
        [
            {"direction": "north", "temp_celsius": 100.0},
            {"direction": "south", "temp_celsius": 95.0},
            {"direction": "east", "temp_celsius": 70.0},
            {"direction": "west", "temp_celsius": 40.0},
        ]
    )
    assert nsew_asymmetry(frame) == 30.0


def test_latest_center_temp_scans_backwards():
    window = [
        _frame_dict([{"direction": "center", "temp_celsius": 150.0}]),
        {"thermal_snapshots": []},  # non-thermal frame skipped
        _frame_dict([{"direction": "CENTER", "temp_celsius": 180.0}]),
        {"thermal_snapshots": []},
    ]
    assert latest_center_temp(window) == 180.0
    assert latest_center_temp([{"thermal_snapshots": []}]) == -1.0
    assert latest_center_temp([]) == -1.0


def test_north_south_mean_delta_zero_when_one_side_missing():
    from warpsense.contracts.frame import Frame

    frame = Frame(timestamp_ms=0, volts=22.0, amps=150.0)
    assert north_south_mean_delta([frame]) == 0.0


# ── consumer aliases stay wired ─────────────────────────────────────────────

def test_warp_features_aliases_point_at_signal():
    from warpsense.features import warp_features

    assert warp_features.extract_asymmetry is nsew_asymmetry
    assert warp_features._safe_float is safe_float
