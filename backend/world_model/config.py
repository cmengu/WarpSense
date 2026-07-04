"""
World-model configuration — every knob lives here (STEPS.md Step 1, decision D1-D11).

CHANNELS order is a contract: x[:, i] in every SessionTensor means CHANNELS[i],
everywhere, forever. Changing the order silently corrupts every trained checkpoint.
"""

from pathlib import Path

# D1 — the 6 input channels. Names match Frame attribute names exactly so the
# Frame → tensor conversion is a getattr, not a mapping table.
CHANNELS = [
    "volts",
    "amps",
    "angle_degrees",
    "travel_angle_degrees",
    "travel_speed_mm_per_min",
    "heat_dissipation_rate_celsius_per_sec",
]
CHANNEL_INDEX = {name: i for i, name in enumerate(CHANNELS)}
N_CHANNELS = len(CHANNELS)

# The 5 control channels that drive the controlled ODE u(t) (STEPS.md Step 7).
# heat_diss is the one OBSERVED consequence, not a control — the welder cannot
# set it directly, so it is excluded from u(t) and is the grounding target (D6).
CONTROL_CHANNELS = CHANNELS[:5]

# D6 — latent structure
LATENT_DIM = 32  # sweep {16, 32, 64} at Gate 2 (Step 12)
PHYS_DIMS = 4    # z[0:4] = z_phys; heat-diss decoder reads ONLY these dims

SEED = 1337
SENSOR_HZ = 100  # ESP32 fixed sample rate; dt = 1/SENSOR_HZ seconds

# D8 — local dev preset (no GPU): every training/eval entry point accepts --tiny
TINY = dict(n_sessions=200, latent=16, epochs=20)

# Split fractions (D9 — by session, never by frame)
SPLIT_FRACTIONS = dict(train=0.70, val=0.15, test=0.15)

# Data locations (repo-root relative, resolved from this file's position)
REPO_ROOT = Path(__file__).resolve().parents[2]
POLITO_DIR = REPO_ROOT / "data" / "public" / "polito_rsw"
EXPERIMENTS_DIR = Path(__file__).resolve().parent / "experiments"
