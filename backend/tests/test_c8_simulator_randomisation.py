"""Tests for C8 ticket #19 — randomised simulator noise/drift and widened ranges.

Three things must hold at once, and they pull against each other:
  1. The new WIDE_RANGES corpus really is more varied — different seeds must
     produce different noise AND drift dictionaries (trap T3: on the noise axis
     the old corpus was a single point).
  2. The widening follows D1 exactly — half-widths ×1.5, midpoints unchanged.
  3. Nothing about the DEFAULT corpus moved. Gate 1.5 and the C4–C7
     reproductions read from sample_params(seed) with no ranges argument, so
     those draws must be identical, value for value, to the pre-C8 sampler.
     The last test pins that against a hardcoded copy of the old sampler.
"""

import math
import random

import numpy as np
import pytest

from world_model.simulator.weld_sim import (
    DEFAULT_DRIFT,
    DEFAULT_NOISE,
    LEGACY_RANGES,
    WIDE_RANGES,
    RandomisationRanges,
    SimParams,
    sample_params,
    simulate_session,
)


# --- 1. drift and noise are actually randomised -----------------------------

def test_wide_ranges_gives_different_noise_and_drift_per_seed():
    a = sample_params(42, ranges=WIDE_RANGES)
    b = sample_params(43, ranges=WIDE_RANGES)
    assert a.noise != b.noise
    assert a.drift != b.drift
    # ...and it is not one scalar applied to the whole dict: the per-key
    # multipliers must differ from each other too.
    ratios = [a.noise[k] / DEFAULT_NOISE[k] for k in DEFAULT_NOISE]
    assert len(set(round(r, 9) for r in ratios)) > 1


def test_wide_ranges_noise_and_drift_stay_within_half_to_double():
    for seed in range(60):
        p = sample_params(seed, ranges=WIDE_RANGES)
        for k, base in DEFAULT_NOISE.items():
            assert 0.5 * base <= p.noise[k] <= 2.0 * base
        for k, base in DEFAULT_DRIFT.items():
            assert 0.5 * base <= p.drift[k] <= 2.0 * base


def test_noise_scale_is_log_uniform_not_uniform():
    """Under log-uniform, ~half the draws land below 1.0×; under uniform, ~1/3."""
    ratios = [sample_params(s, ranges=WIDE_RANGES).noise["volts"] / DEFAULT_NOISE["volts"]
              for s in range(400)]
    below_one = sum(r < 1.0 for r in ratios) / len(ratios)
    assert 0.42 < below_one < 0.58
    # the log of the ratio should be centred on 0 (geometric mean ≈ 1.0)
    assert abs(float(np.mean([math.log(r) for r in ratios]))) < 0.06


def test_randomised_noise_reaches_the_simulated_signal():
    """A noisier parameter draw must show up as noisier sensor readout."""
    base = dict(session_id="s", seed=11, n_frames=600, stitch_on_s=None, stitch_off_s=None)
    quiet = simulate_session(SimParams(**base, noise={**DEFAULT_NOISE, "volts": 0.05}))
    loud = simulate_session(SimParams(**base, noise={**DEFAULT_NOISE, "volts": 1.0}))
    assert np.std(np.diff(loud.x[:, 0])) > 3.0 * np.std(np.diff(quiet.x[:, 0]))


# --- 2. the ranges themselves -----------------------------------------------

@pytest.mark.parametrize("field_name", [
    "volts", "amps", "travel_speed_mm_per_min", "plate_thickness_mm",
    "ambient_c", "stitch_on_s", "stitch_off_s",
])
def test_wide_ranges_are_1p5x_half_width_about_same_midpoint(field_name):
    lo_old, hi_old = getattr(LEGACY_RANGES, field_name)
    lo_new, hi_new = getattr(WIDE_RANGES, field_name)
    mid_old, mid_new = (lo_old + hi_old) / 2, (lo_new + hi_new) / 2
    assert mid_new == pytest.approx(mid_old)
    assert (hi_new - lo_new) == pytest.approx(1.5 * (hi_old - lo_old))


def test_ranges_round_trip_through_persisted_metadata():
    p = sample_params(7, ranges=WIDE_RANGES)
    st = simulate_session(p)
    recorded = st.meta["params"]["ranges"]
    assert recorded["name"] == "wide_c8"
    assert RandomisationRanges.from_dict(recorded) == WIDE_RANGES
    # survives a JSON-ish round-trip (tuples become lists and back)
    import json
    assert RandomisationRanges.from_dict(json.loads(json.dumps(recorded))) == WIDE_RANGES


def test_custom_ranges_are_honoured_and_recorded():
    custom = RandomisationRanges(
        name="unit_test", volts=(20.0, 20.0), amps=(100.0, 100.0),
        travel_speed_mm_per_min=(300.0, 300.0), plate_thickness_mm=(6.0, 6.0),
        ambient_c=(25.0, 25.0), stitch_on_s=(2.0, 2.0), stitch_off_s=(0.3, 0.3),
    )
    p = sample_params(1, ranges=custom)
    assert p.volts == 20.0 and p.amps == 100.0
    assert p.noise == DEFAULT_NOISE  # no noise_scale → left alone
    assert p.ranges["name"] == "unit_test"


def test_sampling_is_reproducible_from_seed_and_ranges():
    assert sample_params(99, ranges=WIDE_RANGES) == sample_params(99, ranges=WIDE_RANGES)


def test_wide_draws_land_outside_the_legacy_ranges():
    """The point of widening: some sessions must fall where the old corpus never did."""
    outside = sum(
        not (LEGACY_RANGES.amps[0] <= sample_params(s, ranges=WIDE_RANGES).amps
             <= LEGACY_RANGES.amps[1])
        for s in range(200)
    )
    assert outside > 0


# --- 3. the default corpus did not move -------------------------------------

def _pre_c8_sampler(seed: int) -> dict:
    """Verbatim copy of the pre-C8 sample_params() draw sequence."""
    rng = random.Random(seed)
    stitch = rng.random() < 0.5
    return dict(
        volts=rng.uniform(18.0, 26.0),
        amps=rng.uniform(90.0, 200.0),
        travel_speed_mm_per_min=rng.uniform(150.0, 450.0),
        plate_thickness_mm=rng.uniform(3.0, 10.0),
        ambient_c=rng.uniform(10.0, 35.0),
        stitch_on_s=rng.uniform(1.5, 3.0) if stitch else None,
        stitch_off_s=rng.uniform(0.2, 0.6) if stitch else None,
    )


@pytest.mark.parametrize("seed", [0, 1, 42, 1337, 99999])
def test_default_sampling_is_byte_identical_to_pre_c8(seed):
    p = sample_params(seed)
    for k, v in _pre_c8_sampler(seed).items():
        assert getattr(p, k) == v
    assert p.drift == DEFAULT_DRIFT
    assert p.noise == DEFAULT_NOISE
    assert p.ranges["name"] == "legacy"


def test_default_simulated_signal_unchanged_by_ranges_plumbing():
    """Same seed, no ranges argument → the tensor a Gate 1.5 rerun would see."""
    a = simulate_session(sample_params(5))
    b = simulate_session(SimParams(session_id="goldak_00005", seed=5,
                                   **_pre_c8_sampler(5)))
    assert np.array_equal(a.x, b.x)
    assert np.array_equal(a.meta["fusion_depth_mm"], b.meta["fusion_depth_mm"])
