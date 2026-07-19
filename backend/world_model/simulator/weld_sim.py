"""
weld_sim.py generates synthetic weld sessions with a KNOWN per-frame fusion
depth: SessionTensor with x[T,6] sensor channels plus meta["fusion_depth_mm"][T]
— the hidden-state label no real sensor can provide (STEPS.md Step 4).

For newcomers — how one simulated session is built, frame by frame (100 Hz):
  1. Control profiles. The commanded volts/amps/travel-speed/angles wander
     slowly around their setpoints (mean-reverting random walk) — a welder's
     hand is not a servo. A stitch schedule optionally switches the arc
     on/off in a cycle; during arc-off, current is ~0 and the torch dwells.
  2. Physics. Each frame's TRUE control values feed goldak.fusion_zone_depth
     to get the quasi-steady depth the pool is heading toward. Because
     Rosenthal assumes steady state, the actual depth follows it through a
     first-order lag (time constant TAU_POOL_S) — so depth ramps up after
     every arc start and decays during arc-off, producing the characteristic
     dip at stitch restarts (the lack-of-fusion failure mode). Off-angle
     torch positions waste arc power via a cosine factor.
  3. Heat-dissipation channel. A lumped pool temperature integrates
     heating (absorbed power / thermal mass) against Newtonian cooling; the
     cooling term k_cool*(T_pool - ambient) IS the heat_diss channel (°C/s),
     mirroring how the real sensor derives it.
  4. Sensor readout. The 6 channels record the true values PLUS Gaussian
     sensor noise (physics is driven by the clean values; only the readout
     is noisy). The depth label in meta stays clean — it is ground truth.

  sample_params() draws randomised sessions (domain randomisation) — the
  corpus generator for Steps 5 and 10. Whole regions of that parameter space
  (e.g. plate-thickness extremes) get reserved as the OOD split (D9).

How wide is "randomised"? — RandomisationRanges (C8 trap T3, decision D1)

  Domain randomisation only works if the real world lands INSIDE the training
  distribution. The original ranges failed that test on one axis: they varied
  six physical quantities but left `drift` and `noise` at their dataclass
  defaults, so every session in the corpus shared one identical sensor-noise
  signature — a single point, which real hardware is guaranteed to miss.

  The fix is a RandomisationRanges object: the ranges are now an explicit,
  recorded PARAMETER of the corpus rather than constants buried in the sampler.
  A corpus is reproducible from (seed, ranges), and the ranges round-trip
  through meta["params"]["ranges"] so any stored session says exactly which
  distribution produced it.

  Two are predefined:
    LEGACY_RANGES (the default) — the pre-C8 ranges, with drift/noise NOT
      randomised. Keeping this the default is what makes earlier corpora
      (Gate 1.5, C4–C7) reproduce bit-for-bit: same seed, same draws, same
      order, no extra rng consumption.
    WIDE_RANGES (opt-in, D1) — the six physical half-widths ×1.5 around
      unchanged midpoints, plus per-session drift and noise drawn log-uniform
      over [0.5×, 2.0×] their defaults, independently per key.

  Pass one explicitly: sample_params(seed, ranges=WIDE_RANGES).

Any metric computed on this data is meaningful only after Gate 1 calibrates
the simulator against real sectioned coupons (STEPS.md Step 9).
"""

import math
import random
from dataclasses import asdict, dataclass, field

import numpy as np

from world_model.config import SENSOR_HZ
from world_model.data.schema import SessionTensor
from world_model.simulator.goldak import fusion_zone_depth

# Pool response lag (s): how fast actual depth chases the quasi-steady value.
TAU_POOL_S = 0.5
# Lumped pool thermal model (tuned for plausible magnitudes, calibrated at Gate 1)
C_THERMAL_J_PER_K = 20.0   # effective thermal mass of the pool region, J/K
K_COOLING_PER_S = 0.5      # Newtonian cooling constant, 1/s

WORK_ANGLE_TARGET = 90.0   # degrees; deviation wastes arc power
TRAVEL_ANGLE_TARGET = 10.0


@dataclass
class SimParams:
    session_id: str = "goldak_000"
    seed: int = 0
    n_frames: int = 1500                     # 15 s at 100 Hz
    volts: float = 22.0
    amps: float = 130.0
    travel_speed_mm_per_min: float = 250.0
    plate_thickness_mm: float = 6.0
    ambient_c: float = 25.0
    # stitch schedule; None → continuous weld
    stitch_on_s: float | None = 2.2
    stitch_off_s: float | None = 0.3
    # control-drift and sensor-noise scales (std devs)
    drift: dict = field(default_factory=lambda: dict(
        volts=0.4, amps=4.0, speed=12.0, work_angle=2.5, travel_angle=2.0))
    noise: dict = field(default_factory=lambda: dict(
        volts=0.15, amps=1.5, speed=4.0, angle=0.4, heat_diss=1.5))
    # which randomisation distribution produced this session (see RandomisationRanges)
    ranges: dict = field(default_factory=lambda: LEGACY_RANGES.as_dict())


# The dataclass defaults above, as plain dicts — the 1.0× anchor that
# WIDE_RANGES' log-uniform multipliers scale.
DEFAULT_DRIFT = dict(volts=0.4, amps=4.0, speed=12.0, work_angle=2.5, travel_angle=2.0)
DEFAULT_NOISE = dict(volts=0.15, amps=1.5, speed=4.0, angle=0.4, heat_diss=1.5)


def _widen(lo: float, hi: float, factor: float = 1.5) -> tuple[float, float]:
    """Scale a range's half-width by `factor`, leaving its midpoint alone (D1)."""
    mid, half = (lo + hi) / 2.0, (hi - lo) / 2.0
    return (mid - half * factor, mid + half * factor)


@dataclass(frozen=True)
class RandomisationRanges:
    """The distribution sample_params() draws from — a recorded parameter, not a constant.

    Each physical field is an inclusive (low, high) uniform range. `drift_scale`
    and `noise_scale` are (low, high) MULTIPLIER ranges applied log-uniformly to
    DEFAULT_DRIFT / DEFAULT_NOISE, independently per key; `None` means "don't
    randomise that dict at all", which is the pre-C8 behaviour and therefore the
    default. `name` is carried purely so a stored corpus is self-describing.
    """

    name: str
    volts: tuple[float, float]
    amps: tuple[float, float]
    travel_speed_mm_per_min: tuple[float, float]
    plate_thickness_mm: tuple[float, float]
    ambient_c: tuple[float, float]
    stitch_on_s: tuple[float, float]
    stitch_off_s: tuple[float, float]
    drift_scale: tuple[float, float] | None = None
    noise_scale: tuple[float, float] | None = None

    def as_dict(self) -> dict:
        """JSON/asdict-friendly form — lists, so it survives a serialisation round-trip."""
        d = asdict(self)
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in d.items()}

    @classmethod
    def from_dict(cls, d: dict) -> "RandomisationRanges":
        """Inverse of as_dict(): rebuild the ranges recorded in a persisted corpus."""
        kw = {k: (tuple(v) if isinstance(v, (list, tuple)) else v) for k, v in d.items()}
        return cls(**kw)


# Pre-C8 ranges, drift/noise left at their dataclass defaults. Default on
# purpose: every existing corpus (Gate 1.5, C4–C7) must reproduce exactly.
LEGACY_RANGES = RandomisationRanges(
    name="legacy",
    volts=(18.0, 26.0),
    amps=(90.0, 200.0),
    travel_speed_mm_per_min=(150.0, 450.0),
    plate_thickness_mm=(3.0, 10.0),
    ambient_c=(10.0, 35.0),
    stitch_on_s=(1.5, 3.0),
    stitch_off_s=(0.2, 0.6),
)

# C8/D1: half-widths ×1.5 around unchanged midpoints, plus per-session
# drift and noise over [0.5×, 2.0×] their defaults.
WIDE_RANGES = RandomisationRanges(
    name="wide_c8",
    volts=_widen(*LEGACY_RANGES.volts),
    amps=_widen(*LEGACY_RANGES.amps),
    travel_speed_mm_per_min=_widen(*LEGACY_RANGES.travel_speed_mm_per_min),
    plate_thickness_mm=_widen(*LEGACY_RANGES.plate_thickness_mm),
    ambient_c=_widen(*LEGACY_RANGES.ambient_c),
    stitch_on_s=_widen(*LEGACY_RANGES.stitch_on_s),
    stitch_off_s=_widen(*LEGACY_RANGES.stitch_off_s),
    drift_scale=(0.5, 2.0),
    noise_scale=(0.5, 2.0),
)


def _log_uniform_scaled(rng: random.Random, base: dict,
                        lo_hi: tuple[float, float]) -> dict:
    """Scale every value in `base` by its own log-uniform draw from [lo, hi].

    Log-uniform (not uniform) so that halving and doubling are equally likely —
    a noise level is a scale, and 0.5× should be as reachable as 2×.
    """
    lo, hi = lo_hi
    log_lo, log_hi = math.log(lo), math.log(hi)
    return {k: v * math.exp(rng.uniform(log_lo, log_hi)) for k, v in base.items()}


def sample_params(seed: int, session_id: str | None = None,
                  ranges: RandomisationRanges | None = None) -> SimParams:
    """Domain-randomised parameters (Steps 5/10). One rng per session — reproducible.

    `ranges` defaults to LEGACY_RANGES, which draws exactly the pre-C8 values in
    exactly the pre-C8 order and consumes no extra rng — so old seeds still give
    old corpora. Pass WIDE_RANGES for the C8/D1 distribution.
    """
    r = ranges or LEGACY_RANGES
    rng = random.Random(seed)
    stitch = rng.random() < 0.5
    p = SimParams(
        session_id=session_id or f"goldak_{seed:05d}",
        seed=seed,
        volts=rng.uniform(*r.volts),
        amps=rng.uniform(*r.amps),
        travel_speed_mm_per_min=rng.uniform(*r.travel_speed_mm_per_min),
        plate_thickness_mm=rng.uniform(*r.plate_thickness_mm),
        ambient_c=rng.uniform(*r.ambient_c),
        stitch_on_s=rng.uniform(*r.stitch_on_s) if stitch else None,
        stitch_off_s=rng.uniform(*r.stitch_off_s) if stitch else None,
        ranges=r.as_dict(),
    )
    # Drawn last so enabling them cannot shift the physical draws above.
    if r.drift_scale is not None:
        p.drift = _log_uniform_scaled(rng, DEFAULT_DRIFT, r.drift_scale)
    if r.noise_scale is not None:
        p.noise = _log_uniform_scaled(rng, DEFAULT_NOISE, r.noise_scale)
    return p


def _arc_on_schedule(p: SimParams) -> np.ndarray:
    if p.stitch_on_s is None or p.stitch_off_s is None:
        return np.ones(p.n_frames, dtype=bool)
    on_n = max(int(p.stitch_on_s * SENSOR_HZ), 1)
    off_n = max(int(p.stitch_off_s * SENSOR_HZ), 1)
    cycle = np.r_[np.ones(on_n, dtype=bool), np.zeros(off_n, dtype=bool)]
    return np.tile(cycle, p.n_frames // len(cycle) + 1)[:p.n_frames]


def _drift_walk(rng: np.random.Generator, n: int, base: float, sigma: float,
                reversion: float = 0.02) -> np.ndarray:
    """Mean-reverting random walk around `base` (human-hand control drift)."""
    out = np.empty(n)
    x = base
    for i in range(n):
        x += rng.normal(0.0, sigma * 0.05) - reversion * (x - base)
        out[i] = x
    return out


def simulate_session(p: SimParams) -> SessionTensor:
    rng = np.random.default_rng(p.seed)
    dt = 1.0 / SENSOR_HZ
    T = p.n_frames
    arc_on = _arc_on_schedule(p)

    # 1. true (clean) control profiles
    volts = _drift_walk(rng, T, p.volts, p.drift["volts"])
    amps = _drift_walk(rng, T, p.amps, p.drift["amps"])
    speed = _drift_walk(rng, T, p.travel_speed_mm_per_min, p.drift["speed"])
    work_angle = _drift_walk(rng, T, WORK_ANGLE_TARGET, p.drift["work_angle"])
    travel_angle = _drift_walk(rng, T, TRAVEL_ANGLE_TARGET, p.drift["travel_angle"])

    # 2+3. physics loop: depth lag + lumped pool temperature
    depth_mm = np.zeros(T)
    heat_diss = np.zeros(T)
    d = 0.0
    t_pool = p.ambient_c
    for i in range(T):
        if arc_on[i]:
            angle_factor = (math.cos(math.radians(work_angle[i] - WORK_ANGLE_TARGET))
                            * math.cos(math.radians((travel_angle[i] - TRAVEL_ANGLE_TARGET) / 2.0)))
            d_target_mm = 1000.0 * fusion_zone_depth(
                volts[i], amps[i], speed[i],
                ambient_c=p.ambient_c, angle_factor=max(angle_factor, 0.0))
            d_target_mm = min(d_target_mm, p.plate_thickness_mm)  # can't melt past the plate
            power = 0.8 * volts[i] * amps[i] * max(angle_factor, 0.0)
        else:
            d_target_mm = 0.0
            power = 0.0
        d += (dt / TAU_POOL_S) * (d_target_mm - d)
        depth_mm[i] = d
        cooling = K_COOLING_PER_S * (t_pool - p.ambient_c)
        t_pool += dt * (power / C_THERMAL_J_PER_K - cooling)
        heat_diss[i] = cooling  # °C/s — what the real sensor path derives

    # 4. sensor readout: true values + noise; arc-off reads ~0 current / dwelling torch
    n = p.noise
    x = np.stack([
        np.where(arc_on, volts + rng.normal(0, n["volts"], T), rng.normal(0, n["volts"], T)),
        np.where(arc_on, amps + rng.normal(0, n["amps"], T), np.abs(rng.normal(0, n["amps"], T))),
        work_angle + rng.normal(0, n["angle"], T),
        travel_angle + rng.normal(0, n["angle"], T),
        np.where(arc_on, speed + rng.normal(0, n["speed"], T),
                 np.abs(rng.normal(0, n["speed"], T))),
        np.clip(heat_diss + rng.normal(0, n["heat_diss"], T), 0.0, None),
    ], axis=1).astype(np.float32)

    meta = {
        "session_id": p.session_id,
        "source": "goldak",
        "params": asdict(p),
        "fusion_depth_mm": depth_mm.astype(np.float32),  # clean ground truth
        "arc_on": arc_on,
    }
    return SessionTensor(x=x, mask=np.ones_like(x, dtype=bool), meta=meta)
