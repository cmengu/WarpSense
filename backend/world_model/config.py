"""
config.py holds every world-model constant — channel order, latent dims, splits, paths — so all code shares one contract (STEPS.md D1–D11).

CHANNELS order is a contract: x[:, i] in every SessionTensor means CHANNELS[i],
everywhere, forever. Changing the order silently corrupts every trained checkpoint.

For newcomers — Step 1 (STEPS.md) built four things, all under data/:
  1. schema.py       — SessionTensor, the ONE canonical format every data source
                       is converted into (x[T,6] values + mask[T,6] availability
                       + meta dict). Nothing downstream sees raw formats.
  2. loader_*.py     — converters INTO that format: mock (dev-only fake data),
                       polito (real spot-welding CSVs, 2 of 6 channels), esp32
                       (real captures; stub until Gate 0 data exists).
  3. splits.py       — deterministic 70/15/15 train/val/test partition, by
                       SESSION (never by frame — frame splits leak and inflate
                       metrics). SPLIT_FRACTIONS below is where 70/15/15 lives.
  4. this file       — the shared constants those modules (and everything after
                       them) read, so there is exactly one source of truth.
Step 2 added viz/timeline.py (plot any SessionTensor). Step 3 added the GRU
baseline + eval harness (see baselines/gru_baseline.py for that overview).
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
# the welder can set volts/amps/angles/speed, but heat dissipation is a consequence — so it's excluded from u(t) and becomes the physics grounding target instead. 
CONTROL_CHANNELS = CHANNELS[:5]

# D6 — latent structure
LATENT_DIM = 32  # sweep {16, 32, 64} at Gate 2 (Step 12)
PHYS_DIMS = 4    # z[0:4] = z_phys; heat-diss decoder reads ONLY these dims

SEED = 1337
SENSOR_HZ = 100  # ESP32 fixed sample rate; dt = 1/SENSOR_HZ seconds

# Quality label contract — index order matches WeldClassifier's classes so the
# world-model quality head is drop-in compatible with downstream consumers.
QUALITY_CLASSES = ["GOOD", "MARGINAL", "DEFECTIVE"]
QUALITY_INDEX = {name: i for i, name in enumerate(QUALITY_CLASSES)}

# D8 — local dev preset (no GPU): every training/eval entry point accepts --tiny
TINY = dict(n_sessions=200, latent=16, epochs=20)

# Split fractions (D9 — by session, never by frame)
SPLIT_FRACTIONS = dict(train=0.70, val=0.15, test=0.15)

# Data locations (repo-root relative, resolved from this file's position)
REPO_ROOT = Path(__file__).resolve().parents[2]
POLITO_DIR = REPO_ROOT / "data" / "public" / "polito_rsw"
EXPERIMENTS_DIR = Path(__file__).resolve().parent / "experiments"
