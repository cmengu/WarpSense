"""
Step 4 tests (STEPS.md): the Goldak/Rosenthal simulator must get the PHYSICS
DIRECTIONS right — depth rises with current, falls with travel speed, dips at
stitch restarts — and emit valid SessionTensors with a per-frame depth label.
Absolute accuracy is Gate 1's job (calibration vs sectioned coupons), not ours.
"""

import numpy as np
import pytest

from world_model.simulator.goldak import ETA, GoldakHeatSource, fusion_zone_depth
from world_model.simulator.weld_sim import SimParams, sample_params, simulate_session


# --- fusion_zone_depth: the three directions of change (unit level) ---

def test_depth_increases_with_current():
    depths = [fusion_zone_depth(22.0, I, 250.0) for I in (100.0, 130.0, 180.0)]
    assert depths[0] < depths[1] < depths[2]


def test_depth_decreases_with_travel_speed():
    depths = [fusion_zone_depth(22.0, 130.0, v) for v in (150.0, 300.0, 450.0)]
    assert depths[0] > depths[1] > depths[2]


def test_depth_zero_without_power():
    assert fusion_zone_depth(0.0, 0.0, 250.0) == 0.0
    assert fusion_zone_depth(22.0, 130.0, 250.0, angle_factor=0.0) == 0.0


def test_depth_plausible_magnitude():
    # nominal Al GMAW settings should melt millimetres, not microns or metres
    d_mm = 1000.0 * fusion_zone_depth(22.0, 130.0, 250.0)
    assert 0.5 < d_mm < 15.0


# --- Goldak double ellipsoid: energy conservation ---

def test_power_density_integrates_to_absorbed_power():
    src = GoldakHeatSource()
    V, I = 22.0, 130.0
    Q = ETA * V * I
    # Goldak deposits power into the workpiece HALF-SPACE only (z one side of
    # the surface); the standard coefficients integrate to Q over that half —
    # integrating all of z would double-count to 2Q.
    lim = 0.03
    n = 120
    dx = 2 * lim / n
    dz = lim / n
    xs = -lim + (np.arange(n) + 0.5) * dx   # midpoint samples: the density peaks
    ys = -lim + (np.arange(n) + 0.5) * dx   # at 0, and edge-sampling the peak
    zs = (np.arange(n) + 0.5) * dz          # plane overweights the sum
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    q = src.power_density(X, Y, Z, t=0.0, V=V, I=I, v=0.0)
    total = q.sum() * dx * dx * dz
    assert total == pytest.approx(Q, rel=0.05)


# --- simulate_session: session-level behaviour ---

def test_session_tensor_is_valid_and_labelled():
    st = simulate_session(SimParams(session_id="goldak_test", seed=7))
    assert st.x.shape == (1500, 6)
    assert st.mask.all()  # simulator senses all 6 channels
    assert st.meta["source"] == "goldak"
    d = st.meta["fusion_depth_mm"]
    assert d.shape == (1500,)
    assert np.isfinite(d).all() and (d >= 0).all()
    assert d.max() <= st.meta["params"]["plate_thickness_mm"] + 1e-6


def test_depth_dips_at_stitch_restarts():
    st = simulate_session(SimParams(seed=3, stitch_on_s=2.0, stitch_off_s=0.4))
    d = st.meta["fusion_depth_mm"]
    arc = st.meta["arc_on"]
    restarts = np.flatnonzero(~arc[:-1] & arc[1:]) + 1
    assert len(restarts) >= 3
    for r in restarts:
        on_end = r
        while on_end < len(arc) and arc[on_end]:
            on_end += 1
        if on_end - r < 50:
            continue
        just_after_restart = d[r + 10]
        late_in_stitch = d[on_end - 10]
        assert just_after_restart < 0.7 * late_in_stitch


def test_session_depth_tracks_current_and_speed():
    base = dict(seed=11, stitch_on_s=None, stitch_off_s=None)
    nominal = simulate_session(SimParams(**base, amps=130.0))
    hot = simulate_session(SimParams(**base, amps=180.0))
    fast = simulate_session(SimParams(**base, travel_speed_mm_per_min=450.0))
    mean_depth = lambda st: st.meta["fusion_depth_mm"][200:].mean()  # skip ramp-in
    assert mean_depth(hot) > mean_depth(nominal) > mean_depth(fast)


def test_sample_params_deterministic_and_in_range():
    a, b = sample_params(42), sample_params(42)
    assert a == b
    assert sample_params(42) != sample_params(43)
    p = sample_params(42)
    assert 18.0 <= p.volts <= 26.0
    assert 3.0 <= p.plate_thickness_mm <= 10.0
