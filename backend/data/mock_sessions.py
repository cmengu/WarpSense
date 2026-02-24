"""
Mock session data generation for canonical time-series contract.

PHYSICAL MODEL
--------------
All sensor values are causally linked — changing one affects the others:

  angle_degrees (work angle: torch tilt left/right across the seam)
    → drives north/south temperature ASYMMETRY
    → 0° = perfectly vertical = symmetric north/south
    → positive angle = tilts toward north side = north hotter, south cooler
    → effect: north_offset = +angle * ANGLE_THERMAL_SENSITIVITY
              south_offset = -angle * ANGLE_THERMAL_SENSITIVITY

  arc_power_watts = volts × amps
    → drives center temperature MAGNITUDE
    → more power = hotter center at every distance
    → effect: center_temp = BASE_TEMP + (arc_power - NOMINAL_POWER) * POWER_THERMAL_SENSITIVITY
    → also drives heat dissipation rate: hotter = steeper cooling gradient

  distance_mm (distance along weld seam from torch)
    → drives temperature DROP from center outward
    → models conduction cooling: temp falls exponentially with distance
    → east (direction of travel) stays hotter than west (already passed)

  heat_dissipation_rate_celsius_per_sec
    → = (prev_center_temp - curr_center_temp) / 0.1
    → expert: slow, consistent cooling ~20-40°C/sec
    → novice: erratic, swings with amps spikes ~10-120°C/sec

WHAT THIS MEANS FOR COMPARISON
--------------------------------
  Expert vs Novice produces visible deltas on every metric:
  - Amps: expert flat, novice spiky → large amps_delta swings
  - Volts: expert stable, novice drifting → growing volts_delta over time
  - Angle: expert ~45°, novice drifts to ~65° → angle_degrees_delta increases
  - Thermals: expert symmetric north/south, novice asymmetric → TemperatureDelta visible
  - Heat dissipation: expert smooth, novice erratic → large delta swings
"""

import math
import random
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

from models.frame import Frame
from models.session import Session, SessionStatus
from models.thermal import TemperaturePoint, ThermalSnapshot

# ---------------------------------------------------------------------------
# Sensor configuration
# ---------------------------------------------------------------------------

THERMAL_SAMPLE_INTERVAL_MS = 100       # Thermal fires every 100ms (5Hz thermal)
THERMAL_DISTANCE_INTERVAL_MM = 10.0    # 10mm between snapshot distances
SENSOR_SAMPLE_RATE_HZ = 100            # 100Hz electrical sensors (10ms per frame)
THERMAL_DIRECTIONS = ["center", "north", "south", "east", "west"]

# 5 distances along the weld seam (constant across all sessions — Session validator requires this)
THERMAL_DISTANCES_MM = [10.0, 20.0, 30.0, 40.0, 50.0]

# ---------------------------------------------------------------------------
# Physical constants (tuned to mild steel MIG welding)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Aluminum 6061 constants (used by stitch_expert / continuous_novice generators)
# ---------------------------------------------------------------------------

# Electrical — from PubMed Central / ScienceDirect research on 6061-T6
AL_AMPS                      = 155.0   # A — center of 130–180A range for 3–6mm
AL_VOLTS                     = 22.0    # V — center of 21–24V range for spray transfer
AL_AMPS_NOISE_EXPERT         =   4.0   # σ A — expert tremor
AL_AMPS_NOISE_NOVICE         =  10.0   # σ A — novice instability (2.5× expert)
AL_VOLTS_NOISE_NORMAL        =   0.3   # σ V — stable arc
AL_VOLTS_NOISE_POROSITY      =   1.8   # σ V — elevated during porosity event

# Travel speed — AWS D1.2 table for 3–6mm aluminum GMAW spray transfer
AL_TRAVEL_SPEED_NOMINAL      = 470.0   # mm/min — expert center target
AL_TRAVEL_SPEED_EXPERT_MIN   = 380.0   # mm/min — expert lower bound
AL_TRAVEL_SPEED_EXPERT_MAX   = 560.0   # mm/min — expert upper bound
AL_TRAVEL_SPEED_NOISE_EXPERT =   8.0   # σ mm/min — expert micro-variation
AL_TRAVEL_SPEED_NOISE_NOVICE =  20.0   # σ mm/min — novice baseline noise
AL_TRAVEL_SPEED_FLOOR        = 200.0   # mm/min — absolute minimum (novice dwell)
AL_TRAVEL_SPEED_CEILING      = 700.0   # mm/min — absolute maximum

# Porosity — Welding Journal: porosity shows as elevated voltage σ, not elevated mean
AL_POROSITY_PROB_NOVICE      = 0.0030  # per arc-on frame, cause-gated (see Step 4)
AL_POROSITY_PROB_EXPERT      = 0.00030 # 10× less than novice
AL_POROSITY_MIN_FRAMES       =    20   # minimum event duration frames
AL_POROSITY_MAX_FRAMES       =    40   # maximum event duration frames

# Thermal — aluminum specific heat 0.896 J/g·°C, density 2.70 g/cm³
AL_AMBIENT_TEMP              =  25.0   # °C
AL_MELT_POINT                = 660.0   # °C — 6061 solidus ~582°C, liquidus ~652°C

AL_DISSIPATION_COEFF = 0.09
AL_MAX_TEMP = 480.0
AL_CONDUCTIVITY_AXIAL = 0.035    # heat flow 10→20→30→40→50mm per frame
AL_CONDUCTIVITY_LATERAL = 0.045  # heat flow center→N/S/E/W per frame
AL_CONDUCTIVITY_EW_RATIO = 0.6   # east/west conduct less (not on arc axis)
AL_ARC_INPUT_DISTANCE_MM = 10    # arc energy enters at closest node only

# ---------------------------------------------------------------------------
# Aluminum thermal grid physics (NEW; used only by aluminum generators)
# ---------------------------------------------------------------------------

ThermalState = Dict[float, Dict[str, float]]


def _init_thermal_state(ambient: float) -> ThermalState:
    return {
        dist: {d: ambient for d in ("center", "north", "south", "east", "west")}
        for dist in THERMAL_DISTANCES_MM
    }


def _step_thermal_state(
    state: ThermalState,
    arc_active: bool,
    angle_degrees: float,
    travel_speed_mm_per_min: float = AL_TRAVEL_SPEED_NOMINAL,
) -> ThermalState:
    new = {dist: dict(dirs) for dist, dirs in state.items()}

    # 1) Arc input at 10mm only (closest node)
    if arc_active:
        # In the 5×5 thermal grid, dissipation is applied per-node. To keep aluminum
        # temperatures in a realistic range (hundreds of °C) we scale arc input.
        speed_scale = AL_TRAVEL_SPEED_NOMINAL / travel_speed_mm_per_min
        heat = ((AL_VOLTS * AL_AMPS) / 1000.0) * 20.0 * speed_scale
        raw_bias = (angle_degrees - 45.0) / 45.0
        bias = math.copysign(min(0.4, abs(raw_bias)), raw_bias)

        d0 = float(AL_ARC_INPUT_DISTANCE_MM)
        new[d0]["center"] += heat * 0.5
        new[d0]["north"] += heat * (0.25 + bias * 0.2)
        new[d0]["south"] += heat * (0.25 - bias * 0.2)

    # 2) Axial conduction (along seam axis: 10→20→30→40→50)
    distances = sorted(THERMAL_DISTANCES_MM)
    for direction in ("center", "north", "south", "east", "west"):
        for i in range(1, len(distances)):
            near, far = distances[i - 1], distances[i]
            delta = (state[near][direction] - state[far][direction]) * AL_CONDUCTIVITY_AXIAL
            new[near][direction] -= delta
            new[far][direction] += delta

    # 3) Lateral conduction (center→N/S/E/W) — reads from new (post arc-input)
    for dist in THERMAL_DISTANCES_MM:
        center_temp = new[dist]["center"]
        for direction in ("north", "south"):
            delta = (center_temp - new[dist][direction]) * AL_CONDUCTIVITY_LATERAL
            new[dist]["center"] -= delta
            new[dist][direction] += delta
        for direction in ("east", "west"):
            delta = (
                (center_temp - new[dist][direction])
                * AL_CONDUCTIVITY_LATERAL
                * AL_CONDUCTIVITY_EW_RATIO
            )
            new[dist]["center"] -= delta
            new[dist][direction] += delta

    # 4) Dissipation (per node)
    for dist in THERMAL_DISTANCES_MM:
        for direction in new[dist]:
            excess = new[dist][direction] - AL_AMBIENT_TEMP
            new[dist][direction] -= AL_DISSIPATION_COEFF * excess
            new[dist][direction] = max(
                AL_AMBIENT_TEMP, min(AL_MAX_TEMP, new[dist][direction])
            )

    return new


def _aluminum_state_to_snapshots(state: ThermalState) -> List[ThermalSnapshot]:
    snapshots: List[ThermalSnapshot] = []
    for dist in THERMAL_DISTANCES_MM:
        d = state[dist]
        readings = [
            TemperaturePoint(direction="center", temp_celsius=d["center"]),
            TemperaturePoint(direction="north", temp_celsius=d["north"]),
            TemperaturePoint(direction="south", temp_celsius=d["south"]),
            TemperaturePoint(direction="east", temp_celsius=d["east"]),
            TemperaturePoint(direction="west", temp_celsius=d["west"]),
        ]
        snapshots.append(ThermalSnapshot(distance_mm=dist, readings=readings))
    return snapshots


def _porosity_probability(
    angle_degrees: float,
    travel_speed_mm_per_min: float,
    ctwd_mm: float,
    base_prob: float,
) -> float:
    """
    Returns per-frame porosity probability gated on physical causes.
    Causes: angle deviation, excessive travel speed, excessive CTWD.
    Physical basis: AWS D1.2 ±10° angle; Lincoln GMAW speed; ESAB CTWD 12–19mm.
    """
    prob = base_prob

    angle_deviation = abs(angle_degrees - 90.0)
    if angle_deviation > 20.0:
        prob *= 4.0
    elif angle_deviation > 10.0:
        prob *= 2.0

    if travel_speed_mm_per_min > 560.0:
        prob *= 3.0
    elif travel_speed_mm_per_min > 500.0:
        prob *= 1.5

    if ctwd_mm > 19.0:
        prob *= 2.5

    return min(prob, 0.10)


def _compute_interpass_bias(stitch_index: int, end_temp_celsius: float) -> float:
    """
    Returns ambient temperature offset for the next stitch based on
    end temperature of previous stitch and fixed cooling time.
    AWS D1.2 specifies max interpass temp 150°C for aluminum.
    Models 30-second interpass pause; aluminum cooling τ ≈ 45s for 3–6mm plate.
    """
    if stitch_index == 0:
        return 0.0
    cooling_tau = 45.0           # seconds — empirical for 3–6mm plate
    interpass_pause = 30.0       # seconds — operator pause between stitches
    cooled_temp = AL_AMBIENT_TEMP + (end_temp_celsius - AL_AMBIENT_TEMP) * (
        math.exp(-interpass_pause / cooling_tau)
    )
    return max(0.0, cooled_temp - AL_AMBIENT_TEMP)


# ---------------------------------------------------------------------------
# Aluminum frame generators (NEW; routed in generate_frames_for_arc later)
# ---------------------------------------------------------------------------


def _generate_stitch_expert_frames(
    session_index: int,
    num_frames: int = 1500,
) -> List[Frame]:
    """
    Aluminum stitch expert:
    - Stitch pattern: 150 frames arc-on, 100 frames arc-off (repeats)
    - Thermal override: if 10mm center > 220°C, force arc off
    - Thermal grid state advances every frame; thermal snapshots emitted every 20 frames (200ms)
    - heat_dissipation_rate set only on thermal frames (cooling-only metric: clamp at 0)

    Uses isolated random.Random(seed) so global random state is never touched — sessions
    remain deterministic even when seeded in parallel or interleaved with other RNG callers.
    """
    rng = random.Random(session_index * 42)

    frames: List[Frame] = []
    thermal_state = _init_thermal_state(AL_AMBIENT_TEMP)
    angle = 45.0
    travel_speed = AL_TRAVEL_SPEED_NOMINAL
    travel_angle = 12.0  # expert push angle, stable
    porosity_frames_remaining = 0
    ctwd_mm = 15.0  # nominal CTWD for aluminum GMAW (ESAB: 12–19mm)

    last_thermal_center_10mm: Optional[float] = None
    thermal_interval_sec = 0.2  # 20 frames × 10ms
    prev_arc_active = False
    last_arc_end_temp = AL_AMBIENT_TEMP
    stitch_count = 0

    for i in range(num_frames):
        arc_active = (i % 250) < 150

        # Thermal override after stitch logic — thermal wins
        center_10mm = thermal_state[10.0]["center"]
        if center_10mm > 220.0:
            arc_active = False

        # Interpass bias: when arc turns on after stitch, apply residual heat from previous stitch
        if prev_arc_active and not arc_active:
            last_arc_end_temp = thermal_state[10.0]["center"]
        if not prev_arc_active and arc_active:
            stitch_count += 1
            if stitch_count > 1:
                bias = _compute_interpass_bias(stitch_count - 1, last_arc_end_temp)
                thermal_state = _init_thermal_state(AL_AMBIENT_TEMP + bias)

        # Angle reacts to thermal state (expert behavior)
        north_10mm = thermal_state[10.0]["north"]
        south_10mm = thermal_state[10.0]["south"]
        if center_10mm > 180.0 and (north_10mm - south_10mm) > 10.0:
            angle_target = 35.0
        elif center_10mm > 220.0:
            angle_target = 90.0
        else:
            angle_target = 45.0

        angle += (angle_target - angle) * 0.03 + rng.gauss(0.0, 1.2)
        angle = max(20.0, min(85.0, angle))

        # Expert: adaptive speed — AWS "weld hot and fast" for aluminum
        temp_at_arc = thermal_state[10.0]["center"]
        if temp_at_arc > 200:
            speed_target = 530.0
        elif temp_at_arc < 80:
            speed_target = 410.0
        else:
            speed_target = AL_TRAVEL_SPEED_NOMINAL
        travel_speed += (speed_target - travel_speed) * 0.02
        travel_speed += rng.gauss(0, AL_TRAVEL_SPEED_NOISE_EXPERT)
        travel_speed = max(AL_TRAVEL_SPEED_EXPERT_MIN, min(AL_TRAVEL_SPEED_EXPERT_MAX, travel_speed))

        ctwd_mm += rng.gauss(0, 0.05)
        ctwd_mm = max(12.0, min(17.0, ctwd_mm))

        travel_angle += rng.gauss(0, 0.5)
        travel_angle = max(8.0, min(18.0, travel_angle))

        thermal_state = _step_thermal_state(thermal_state, arc_active, angle, travel_speed)
        new_center_10mm = thermal_state[10.0]["center"]

        porosity_prob = _porosity_probability(
            angle_degrees=angle,
            travel_speed_mm_per_min=travel_speed,
            ctwd_mm=ctwd_mm,
            base_prob=AL_POROSITY_PROB_EXPERT,
        )
        if arc_active and rng.random() < porosity_prob:
            porosity_frames_remaining = rng.randint(AL_POROSITY_MIN_FRAMES, AL_POROSITY_MAX_FRAMES)
        volts_sigma = AL_VOLTS_NOISE_POROSITY if porosity_frames_remaining > 0 else AL_VOLTS_NOISE_NORMAL
        if porosity_frames_remaining > 0:
            porosity_frames_remaining -= 1
        volts = AL_VOLTS + rng.gauss(0, volts_sigma) if arc_active else 0.0
        amps = AL_AMPS + rng.gauss(0, AL_AMPS_NOISE_EXPERT) if arc_active else 0.0

        is_thermal_frame = (i % 20 == 0)
        snapshots = _aluminum_state_to_snapshots(thermal_state) if is_thermal_frame else []

        heat_dissipation: Optional[float] = None
        if is_thermal_frame:
            if last_thermal_center_10mm is not None:
                heat_dissipation = max(
                    0.0,
                    (last_thermal_center_10mm - new_center_10mm) / thermal_interval_sec,
                )
            last_thermal_center_10mm = new_center_10mm

        prev_arc_active = arc_active

        frames.append(
            Frame(
                timestamp_ms=i * 10,
                volts=volts,
                amps=amps,
                angle_degrees=angle,
                thermal_snapshots=snapshots,
                heat_dissipation_rate_celsius_per_sec=heat_dissipation,
                travel_speed_mm_per_min=travel_speed,
                travel_angle_degrees=travel_angle,
            )
        )

    return frames


def _generate_continuous_novice_frames(
    session_index: int,
    num_frames: int = 1500,
) -> List[Frame]:
    """
    Aluminum continuous novice:
    - Continuous arc with brief accidental breaks: off for 12 frames every 380 frames
    - Angle drifts upward with periodic overcorrection and a one-time wrong correction
    - Thermal grid state advances every frame; thermal snapshots emitted every 20 frames (200ms)
    - heat_dissipation_rate set only on thermal frames (cooling-only metric: clamp at 0)

    Ordering constraints (do not reorder):
      (1) Wrong correction (one-time) when 10mm center first exceeds 200°C
      (2) Periodic overcorrection every 300 frames
      (3) Continuous drift
      (4) Clamp angle to [20, 85]

    Uses isolated random.Random(seed) so global random state is never touched — sessions
    remain deterministic even when seeded in parallel or interleaved with other RNG callers.
    """
    rng = random.Random(session_index * 99)

    frames: List[Frame] = []
    thermal_state = _init_thermal_state(AL_AMBIENT_TEMP)
    drift = 0.0
    wrong_correction_fired = False

    travel_speed = AL_TRAVEL_SPEED_NOMINAL
    travel_angle = 12.0  # novice starts at push, drifts toward perpendicular under load
    porosity_frames_remaining = 0
    ctwd_mm = 15.0
    ctwd_drift_rate = rng.gauss(0, 0.01)

    last_thermal_center_10mm: Optional[float] = None
    thermal_interval_sec = 0.2  # 20 frames × 10ms

    for i in range(num_frames):
        arc_active = not ((i % 380) < 12)

        center_10mm = thermal_state[10.0]["center"]

        # (1) Wrong correction (fires once, before drift reset)
        if (not wrong_correction_fired) and center_10mm > 200.0:
            drift += 15.0
            wrong_correction_fired = True

        # (2) Periodic overcorrection snap
        if i % 300 == 0 and i > 0:
            drift -= 22.0

        # (3) Continuous drift
        # Needs to be strong enough to recover between periodic -22° snaps (300-frame cadence).
        drift += 0.08

        # (4) Clamp
        angle = 45.0 + drift + rng.gauss(0.0, 2.5)
        angle = max(20.0, min(85.0, angle))

        # Novice: panic deceleration — sees bright puddle and slows down
        temp_at_arc = thermal_state[10.0]["center"]
        if temp_at_arc > 200 and rng.random() < 0.06:
            travel_speed -= rng.uniform(40, 100)
        elif temp_at_arc > 200 and rng.random() < 0.01:
            travel_speed += rng.uniform(80, 180)
        travel_speed += rng.gauss(0, AL_TRAVEL_SPEED_NOISE_NOVICE)
        travel_speed = max(AL_TRAVEL_SPEED_FLOOR, min(AL_TRAVEL_SPEED_CEILING, travel_speed))

        ctwd_mm += ctwd_drift_rate
        ctwd_mm = max(10.0, min(25.0, ctwd_mm))
        if ctwd_mm >= 24.0:
            ctwd_drift_rate = -abs(ctwd_drift_rate)
        elif ctwd_mm <= 11.0:
            ctwd_drift_rate = abs(ctwd_drift_rate)

        # Novice travel angle: drifts from 10–15° push toward perpendicular under thermal load
        if temp_at_arc > 180 and rng.random() < 0.02:
            travel_angle += rng.uniform(2, 8)
        travel_angle += rng.gauss(0, 1.5)
        travel_angle = max(5.0, min(90.0, travel_angle))

        thermal_state = _step_thermal_state(thermal_state, arc_active, angle, travel_speed)
        new_center_10mm = thermal_state[10.0]["center"]

        porosity_prob = _porosity_probability(
            angle_degrees=angle,
            travel_speed_mm_per_min=travel_speed,
            ctwd_mm=ctwd_mm,
            base_prob=AL_POROSITY_PROB_NOVICE,
        )
        if arc_active and rng.random() < porosity_prob:
            porosity_frames_remaining = rng.randint(AL_POROSITY_MIN_FRAMES, AL_POROSITY_MAX_FRAMES)
        volts_sigma = AL_VOLTS_NOISE_POROSITY if porosity_frames_remaining > 0 else AL_VOLTS_NOISE_NORMAL
        if porosity_frames_remaining > 0:
            porosity_frames_remaining -= 1
        volts = AL_VOLTS + rng.gauss(0, volts_sigma) if arc_active else 0.0
        amps = AL_AMPS + rng.gauss(0, AL_AMPS_NOISE_NOVICE) if arc_active else 0.0
        if arc_active and rng.random() < 0.003:
            amps += rng.uniform(15, 25)

        is_thermal_frame = (i % 20 == 0)
        snapshots = _aluminum_state_to_snapshots(thermal_state) if is_thermal_frame else []

        heat_dissipation: Optional[float] = None
        if is_thermal_frame:
            if last_thermal_center_10mm is not None:
                heat_dissipation = max(
                    0.0,
                    (last_thermal_center_10mm - new_center_10mm) / thermal_interval_sec,
                )
            last_thermal_center_10mm = new_center_10mm

        frames.append(
            Frame(
                timestamp_ms=i * 10,
                volts=volts,
                amps=amps,
                angle_degrees=angle,
                thermal_snapshots=snapshots,
                heat_dissipation_rate_celsius_per_sec=heat_dissipation,
                travel_speed_mm_per_min=travel_speed,
                travel_angle_degrees=travel_angle,
            )
        )

    return frames

# Nominal operating point
NOMINAL_AMPS = 150.0          # A  — typical MIG welding current for mild steel
NOMINAL_VOLTS = 22.5          # V  — typical MIG arc voltage
NOMINAL_POWER = NOMINAL_AMPS * NOMINAL_VOLTS  # ~3375W

# How much center temperature changes per watt of arc power deviation
# e.g. 100W extra → +30°C at 10mm (closer = more sensitive)
POWER_THERMAL_SENSITIVITY = 0.03   # °C / W

# How much north/south asymmetry per degree of work angle tilt
# e.g. 10° tilt → north is +30°C hotter than south at center distance
ANGLE_THERMAL_SENSITIVITY = 3.0    # °C / degree

# Base center temperature at each distance at nominal power, 0° angle
# Models conduction cooling: hot near arc, cools with distance
BASE_CENTER_TEMPS = {
    10.0: 520.0,   # Very close to arc pool
    20.0: 380.0,
    30.0: 260.0,
    40.0: 170.0,
    50.0:  95.0,   # Far from arc, mostly ambient + conduction
}

# Temperature drop from center to each cardinal direction at each distance
# East (direction of travel) stays hotter — arc is approaching
# West (behind arc) is cooler — already solidified
# North/south determined by angle (see ANGLE_THERMAL_SENSITIVITY above)
BASE_EAST_OFFSET  =  40.0   # °C ABOVE center (preheated metal ahead)
BASE_WEST_OFFSET  = -80.0   # °C BELOW center (solidified behind)
BASE_NS_OFFSET    = -30.0   # °C BELOW center at 0° work angle (symmetric baseline)

# How fast center temperature decays over the session (weld progresses along joint)
# As the arc moves, any fixed point on the joint cools slowly
THERMAL_DECAY_RATE = 0.8    # °C per second of session time

# ---------------------------------------------------------------------------
# Signal generators — expert
# ---------------------------------------------------------------------------

def expert_amps(t: int) -> float:
    """
    Expert: stable ~150A, minimal variation.
    Small warmup oscillation (±2%) that decays quickly — avoids zero crossing,
    stays within 20% continuity limit between frames.
    No initial ramp: starts at nominal immediately to avoid "zero to non-zero" jump.
    """
    # Tiny warmup oscillation that decays to zero over first 500ms
    warmup_phase = max(0.0, 1.0 - t / 500.0)           # 1→0 over first 500ms
    warmup = 3.0 * math.sin(t / 50.0) * warmup_phase   # ±3A decaying oscillation
    
    # Steady-state variation (active throughout)
    slow_sine = 2.0 * math.sin(t / 4000.0)             # ±2A very slow oscillation
    noise = 1.0 * math.sin(t / 200.0 + 0.7)            # ±1A periodic noise
    
    return NOMINAL_AMPS + warmup + slow_sine + noise


def expert_volts(t: int) -> float:
    """
    Expert: stable ~22.5V, tiny variation.
    Volts and amps slightly anti-correlated (arc self-regulates in MIG).
    """
    slow_drift = 0.2 * math.sin(t / 5000.0)
    noise = 0.1 * math.sin(t / 350.0 + 1.2)
    return NOMINAL_VOLTS + slow_drift + noise


def expert_angle(t: int) -> float:
    """
    Expert: holds ~45° work angle, very slight hand tremor (±1°).
    45° is the textbook correct work angle for flat MIG.
    """
    tremor = 1.0 * math.sin(t / 800.0 + 0.3)
    return 45.0 + tremor


# ---------------------------------------------------------------------------
# Signal generators — novice
# ---------------------------------------------------------------------------

def novice_amps(t: int) -> float:
    """
    Novice: erratic current — large oscillations and occasional spikes.
    Novice tends to move the torch inconsistently → arc length varies → amps spike.
    Spikes happen every ~2 seconds and are brief (100ms).
    IMPORTANT: max jump between consecutive frames must stay under 20% (30A at 150A).
    The spike rises/falls smoothly over multiple frames to stay within continuity limit.
    """
    base = 145.0
    # Large slow oscillation (±15A)
    swing = 15.0 * math.sin(t / 600.0)
    # Spike: smooth triangle wave peaking at +25A every 2000ms, 200ms wide
    spike_phase = (t % 2000) / 2000.0       # 0→1 within each 2-second cycle
    if spike_phase < 0.1:                    # Rising edge (200ms)
        spike = 25.0 * (spike_phase / 0.1)
    elif spike_phase < 0.2:                  # Falling edge (200ms)
        spike = 25.0 * (1.0 - (spike_phase - 0.1) / 0.1)
    else:
        spike = 0.0
    return base + swing + spike


def novice_volts(t: int) -> float:
    """
    Novice: voltage drifts downward over session (~18V by end).
    Novice gradually shortens arc → lower voltage.
    Also has more oscillation than expert.
    """
    # Linear drift: 22V → 18V over 15 seconds
    drift = -4.0 * (t / 15000.0)
    swing = 1.5 * math.sin(t / 700.0 + 0.5)
    return 22.0 + drift + swing


def novice_angle(t: int) -> float:
    """
    Novice: work angle drifts from 45° to 65° (over-tilting over time).
    Also has periodic wobble — hand not steady.
    This directly causes north/south thermal asymmetry that grows over time.
    """
    # Linear drift: 45° → 65° over 15 seconds
    drift = 20.0 * (t / 15000.0)
    wobble = 5.0 * math.sin(t / 900.0 + 1.1)
    return 45.0 + drift + wobble


# ---------------------------------------------------------------------------
# Arc-specific signal generators (for welder archetypes)
# ---------------------------------------------------------------------------


def _arc_angle_tight(t: int, session_idx: int) -> float:
    """Tightening: session 0 loose (±4°), session 4 tight (±1°)."""
    looseness = max(0.5, 4.0 - session_idx * 0.8)
    return 45.0 + looseness * math.sin(t / 600.0)


def _arc_angle_drift(t: int, session_idx: int) -> float:
    """Declining: drift grows with drift_factor = 0.15 + session_idx * 0.15."""
    drift_factor = 0.15 + session_idx * 0.15
    drift = 20.0 * drift_factor * (t / 15000.0)
    wobble = 4.0 * math.sin(t / 900.0)
    return 45.0 + drift + wobble


def _arc_amps_stable(t: int) -> float:
    """Stable ±2A."""
    return NOMINAL_AMPS + 2.0 * math.sin(t / 4000.0)


def _arc_amps_unstable(t: int) -> float:
    """Unstable ±8A."""
    return NOMINAL_AMPS + 8.0 * math.sin(t / 500.0)


def _arc_volts_stable(t: int) -> float:
    """Stable ±0.15V."""
    return NOMINAL_VOLTS + 0.15 * math.sin(t / 3500.0)


def _arc_volts_unstable(t: int) -> float:
    """Unstable ±2V."""
    return NOMINAL_VOLTS + 2.0 * math.sin(t / 800.0)


def generate_frames_for_arc(
    arc_type: str,
    session_index: int,
    duration_ms: int = 15_000,
) -> Tuple[List[Frame], bool]:
    """
    Generate frames for an arc type and session index.
    Returns (frames, disable_continuity): volatile/declining need continuity disabled.

    Tuning guide (Step 1.4):
      - If fast_learner scores low → tighten _arc_angle_tight stddev (reduce looseness).
      - If declining scores high → increase _arc_angle_drift drift_factor.
    """
    if arc_type == "stitch_expert":
        num_frames = duration_ms // 10
        return _generate_stitch_expert_frames(session_index, num_frames), True
    if arc_type == "continuous_novice":
        num_frames = duration_ms // 10
        return _generate_continuous_novice_frames(session_index, num_frames), True

    if arc_type == "fast_learner":
        get_angle = lambda t: _arc_angle_tight(t, session_index)
        get_amps = _arc_amps_stable
        get_volts = _arc_volts_stable
        disable = False
    elif arc_type == "declining":
        get_angle = lambda t: _arc_angle_drift(t, session_index)
        get_amps = _arc_amps_stable
        get_volts = _arc_volts_stable
        disable = True
    elif arc_type == "volatile":
        get_angle = lambda t: 45.0 + 6.0 * math.sin(t / 300.0)
        get_amps = _arc_amps_unstable
        get_volts = _arc_volts_unstable
        disable = True
    elif arc_type == "consistent_expert":
        get_angle = expert_angle
        get_amps = expert_amps
        get_volts = expert_volts
        disable = False
    elif arc_type in ("plateaued", "new_hire"):
        get_angle = lambda t: 45.0 + 3.0 * math.sin(t / 700.0)
        get_amps = _arc_amps_stable
        get_volts = _arc_volts_stable
        disable = False
    else:
        get_angle = expert_angle
        get_amps = expert_amps
        get_volts = expert_volts
        disable = False

    frames = generate_frames(
        duration_ms=duration_ms,
        get_amps=get_amps,
        get_volts=get_volts,
        get_angle=get_angle,
        include_thermal_gap=False,
    )
    return frames, disable


def generate_session_for_welder(
    welder_id: str,
    arc_type: str,
    session_index: int,
    session_id: str,
    duration_ms: int = 15_000,
) -> Session:
    """
    Build a Session for a welder at a given session index.
    operator_id = welder_id for traceability.
    Caller passes arc_type from WELDER_ARCHETYPES (avoids circular import).
    """
    frames, disable = generate_frames_for_arc(arc_type, session_index, duration_ms)

    is_aluminum_arc = arc_type in ("stitch_expert", "continuous_novice")

    return Session(
        session_id=session_id,
        operator_id=welder_id,
        start_time=datetime.now(timezone.utc),
        weld_type="aluminum" if is_aluminum_arc else "mild_steel",
        process_type="aluminum" if is_aluminum_arc else "mig",
        thermal_sample_interval_ms=200 if is_aluminum_arc else THERMAL_SAMPLE_INTERVAL_MS,
        thermal_directions=THERMAL_DIRECTIONS,
        thermal_distance_interval_mm=THERMAL_DISTANCE_INTERVAL_MM,
        sensor_sample_rate_hz=SENSOR_SAMPLE_RATE_HZ,
        frames=frames,
        status=SessionStatus.COMPLETE,
        frame_count=len(frames),
        expected_frame_count=len(frames),
        last_successful_frame_index=len(frames) - 1,
        validation_errors=[],
        completed_at=datetime.now(timezone.utc),
        disable_sensor_continuity_checks=True if is_aluminum_arc else disable,
    )


# ---------------------------------------------------------------------------
# Thermal snapshot generator
# (single function — physics model makes expert vs novice emerge from signals)
# ---------------------------------------------------------------------------

def generate_thermal_snapshots(
    timestamp_ms: int,
    amps: float,
    volts: float,
    angle_deg: float,
) -> List[ThermalSnapshot]:
    """
    Generate thermal snapshots driven by current sensor values.

    Physics applied:
      1. arc_power = volts × amps → scales all temperatures
      2. angle_deg → north hotter, south cooler (or vice versa)
      3. distance → exponential conduction cooling away from arc
      4. east stays hotter (preheated), west cooler (solidified)
      5. session progression → slow overall cooling via timestamp
    """
    arc_power = volts * amps
    power_delta = arc_power - NOMINAL_POWER           # Positive = more heat than nominal
    session_age_sec = timestamp_ms / 1000.0
    cooling_offset = session_age_sec * THERMAL_DECAY_RATE   # Overall cooling over time

    # Angle asymmetry: positive angle tilts torch toward north side
    # north gets more direct arc heat, south gets less
    angle_asymmetry = (angle_deg - 45.0) * ANGLE_THERMAL_SENSITIVITY

    snapshots = []

    for distance_mm in THERMAL_DISTANCES_MM:
        # Center temperature: base + power scaling - session cooling
        center_temp = (
            BASE_CENTER_TEMPS[distance_mm]
            + power_delta * POWER_THERMAL_SENSITIVITY
            - cooling_offset
        )
        center_temp = max(20.0, center_temp)   # Never below ambient

        # Cardinal directions
        north_temp = center_temp + BASE_NS_OFFSET + angle_asymmetry
        south_temp = center_temp + BASE_NS_OFFSET - angle_asymmetry
        east_temp  = center_temp + BASE_EAST_OFFSET    # Direction of travel: always warmer
        west_temp  = center_temp + BASE_WEST_OFFSET    # Behind arc: always cooler

        # Clamp all to ambient minimum
        readings = [
            TemperaturePoint(direction="center", temp_celsius=max(20.0, center_temp)),
            TemperaturePoint(direction="north",  temp_celsius=max(20.0, north_temp)),
            TemperaturePoint(direction="south",  temp_celsius=max(20.0, south_temp)),
            TemperaturePoint(direction="east",   temp_celsius=max(20.0, east_temp)),
            TemperaturePoint(direction="west",   temp_celsius=max(20.0, west_temp)),
        ]
        snapshots.append(ThermalSnapshot(distance_mm=distance_mm, readings=readings))

    return snapshots


# ---------------------------------------------------------------------------
# Frame generation
# ---------------------------------------------------------------------------

def generate_frames(
    duration_ms: int,
    get_amps: Callable[[int], float],
    get_volts: Callable[[int], float],
    get_angle: Callable[[int], float],
    include_thermal_gap: bool = False,
) -> List[Frame]:
    """
    Generate all frames for a session.

    Heat dissipation is pre-calculated here (mirrors backend thermal_service.py):
      rate = (prev_center_temp - curr_center_temp) / 0.1   [°C/sec]
      Positive = cooling, Negative = heating

    Edge cases handled:
      - Frame 0: no previous frame → heat_dissipation = None
      - Non-thermal frames: heat_dissipation = None
      - Thermal gap frame: previous interval > 100ms → heat_dissipation = None
      - First thermal frame after gap: heat_dissipation = None (gap breaks continuity)
    """
    frames: List[Frame] = []
    frame_interval_ms = 1000 // SENSOR_SAMPLE_RATE_HZ   # 10ms

    prev_thermal_timestamp_ms: Optional[int] = None
    prev_center_temp: Optional[float] = None

    # Thermal gap: skip one thermal interval at the middle of the session
    thermal_gap_at_ms = (duration_ms // 2 // THERMAL_SAMPLE_INTERVAL_MS) * THERMAL_SAMPLE_INTERVAL_MS if include_thermal_gap else None

    for timestamp_ms in range(0, duration_ms, frame_interval_ms):
        is_thermal_frame = (timestamp_ms % THERMAL_SAMPLE_INTERVAL_MS == 0)

        # Apply thermal gap
        if is_thermal_frame and thermal_gap_at_ms is not None and timestamp_ms == thermal_gap_at_ms:
            is_thermal_frame = False

        # Generate electrical signals
        amps  = get_amps(timestamp_ms)
        volts = get_volts(timestamp_ms)
        angle = get_angle(timestamp_ms)

        # Generate thermal snapshots (driven by current electrical values)
        thermal_snapshots: List[ThermalSnapshot] = []
        if is_thermal_frame:
            thermal_snapshots = generate_thermal_snapshots(timestamp_ms, amps, volts, angle)

        # Pre-calculate heat dissipation
        # Only valid when: current frame has thermal data, previous thermal frame exists,
        # and the interval was exactly THERMAL_SAMPLE_INTERVAL_MS (no gap between them)
        heat_dissipation: Optional[float] = None
        curr_center_temp: Optional[float] = None

        if is_thermal_frame and thermal_snapshots:
            # Extract center temp from first snapshot (closest to arc)
            center_reading = next(
                (r for r in thermal_snapshots[0].readings if r.direction == "center"),
                None,
            )
            if center_reading is not None:
                curr_center_temp = center_reading.temp_celsius

                # Only calculate if previous thermal frame was exactly 100ms ago
                if (
                    prev_center_temp is not None
                    and prev_thermal_timestamp_ms is not None
                    and (timestamp_ms - prev_thermal_timestamp_ms) == THERMAL_SAMPLE_INTERVAL_MS
                ):
                    heat_dissipation = (prev_center_temp - curr_center_temp) / 0.1
                    # Positive = cooling (expected), Negative = heating (unusual spike)

        frame = Frame(
            timestamp_ms=timestamp_ms,
            volts=volts,
            amps=amps,
            angle_degrees=angle,
            thermal_snapshots=thermal_snapshots,
            heat_dissipation_rate_celsius_per_sec=heat_dissipation,
        )
        frames.append(frame)

        # Advance thermal tracking state
        if is_thermal_frame:
            prev_thermal_timestamp_ms = timestamp_ms
            prev_center_temp = curr_center_temp

    return frames


# ---------------------------------------------------------------------------
# Session builders
# ---------------------------------------------------------------------------

def generate_expert_session(
    session_id: str = "sess_expert_001",
    duration_ms: int = 15_000,
) -> Session:
    """
    Expert welder: stable 150A, 22.5V, holds 45° work angle.

    Thermal result:
      - Symmetric north/south temperatures (angle stays near 45°)
      - Consistent center temperature at each distance
      - Smooth, predictable heat dissipation ~20-30°C/sec

    Passes sensor continuity checks (amps/volts don't jump more than 20%/10%).
    """
    frames = generate_frames(
        duration_ms=duration_ms,
        get_amps=expert_amps,
        get_volts=expert_volts,
        get_angle=expert_angle,
        include_thermal_gap=False,
    )
    return Session(
        session_id=session_id,
        operator_id="op_expert_01",
        start_time=datetime.now(timezone.utc),
        weld_type="mild_steel",
        thermal_sample_interval_ms=THERMAL_SAMPLE_INTERVAL_MS,
        thermal_directions=THERMAL_DIRECTIONS,
        thermal_distance_interval_mm=THERMAL_DISTANCE_INTERVAL_MM,
        sensor_sample_rate_hz=SENSOR_SAMPLE_RATE_HZ,
        frames=frames,
        status=SessionStatus.COMPLETE,
        frame_count=len(frames),
        expected_frame_count=len(frames),
        last_successful_frame_index=len(frames) - 1,
        validation_errors=[],
        completed_at=datetime.now(timezone.utc),
        disable_sensor_continuity_checks=False,  # Expert stays within continuity limits
    )


def generate_novice_session(
    session_id: str = "sess_novice_001",
    duration_ms: int = 15_000,
) -> Session:
    """
    Novice welder: erratic amps (spikes), drifting volts, angle drifts 45°→65°.

    Thermal result:
      - Growing north/south asymmetry as angle drifts (north side overheats)
      - Lower overall temps early (less consistent arc), higher during spikes
      - Erratic heat dissipation: swings between 10-120°C/sec
      - Mid-session thermal gap (models dropped thermal frame)

    Sensor continuity disabled: novice amps spikes exceed 20% jump rule.
    The spikes are physically realistic (arc length instability) but too large
    for the continuity validator — this is an intentional test of the escape hatch.
    """
    frames = generate_frames(
        duration_ms=duration_ms,
        get_amps=novice_amps,
        get_volts=novice_volts,
        get_angle=novice_angle,
        include_thermal_gap=True,   # Edge case: mid-session missed thermal reading
    )
    return Session(
        session_id=session_id,
        operator_id="op_novice_01",
        start_time=datetime.now(timezone.utc),
        weld_type="mild_steel",
        thermal_sample_interval_ms=THERMAL_SAMPLE_INTERVAL_MS,
        thermal_directions=THERMAL_DIRECTIONS,
        thermal_distance_interval_mm=THERMAL_DISTANCE_INTERVAL_MM,
        sensor_sample_rate_hz=SENSOR_SAMPLE_RATE_HZ,
        frames=frames,
        status=SessionStatus.COMPLETE,
        frame_count=len(frames),
        expected_frame_count=len(frames),
        last_successful_frame_index=len(frames) - 1,
        validation_errors=[],
        completed_at=datetime.now(timezone.utc),
        disable_sensor_continuity_checks=True,  # Novice spikes exceed continuity limits
    )


def generate_large_session(
    session_id: str = "sess_large_001",
    duration_ms: int = 300_000,  # 5 minutes = 30,000 frames
) -> Session:
    """
    Large session for performance testing (streaming, pagination, frontend rendering).
    Uses expert signals — stable and predictable. Not physically interesting,
    purely for testing system behaviour under 30,000 frame load.
    """
    frames = generate_frames(
        duration_ms=duration_ms,
        get_amps=expert_amps,
        get_volts=expert_volts,
        get_angle=expert_angle,
        include_thermal_gap=False,
    )
    return Session(
        session_id=session_id,
        operator_id="op_perf_test",
        start_time=datetime.now(timezone.utc),
        weld_type="mild_steel",
        thermal_sample_interval_ms=THERMAL_SAMPLE_INTERVAL_MS,
        thermal_directions=THERMAL_DIRECTIONS,
        thermal_distance_interval_mm=THERMAL_DISTANCE_INTERVAL_MM,
        sensor_sample_rate_hz=SENSOR_SAMPLE_RATE_HZ,
        frames=frames,
        status=SessionStatus.COMPLETE,
        frame_count=len(frames),
        expected_frame_count=len(frames),
        last_successful_frame_index=len(frames) - 1,
        validation_errors=[],
        completed_at=datetime.now(timezone.utc),
        disable_sensor_continuity_checks=False,
    )


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "generate_expert_session",
    "generate_novice_session",
    "generate_large_session",
    "generate_frames",
    "generate_thermal_snapshots",
    "generate_frames_for_arc",
    "generate_session_for_welder",
]
