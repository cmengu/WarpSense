"""
goldak.py is the weld physics: a Goldak double-ellipsoid heat source plus a
Rosenthal-type fusion-depth solve for aluminium 6061 (STEPS.md Step 4).

For newcomers — why a simulator at all:
  The world model must learn to predict fusion depth, but depth is invisible
  to the sensors — the only ground truth in the real world is cutting a weld
  open (destructive, ~30 coupons total). A physics simulator is the one place
  where depth is KNOWN at every frame, so it provides the labelled corpus for
  training (Step 10) and for the observability-ceiling test (Step 5).

  Two pieces of physics live here:
  - GoldakHeatSource.power_density: the standard arc-welding heat input model.
    The arc deposits power in a double-ellipsoid blob around the torch (denser
    in front, longer tail behind); integrating the blob over all space gives
    back the total absorbed power eta*V*I. Used for calibration/FEM later.
  - fusion_zone_depth: a Rosenthal moving-point-source solve. Rosenthal's
    solution says the steady temperature at distance r below a moving heat
    source is  T = T0 + Q/(2*pi*k*r) * exp(-v*r/(2*alpha)). The fusion depth
    is the r at which T equals the melting point — found by bisection, since
    temperature falls monotonically with depth. More power → deeper melt;
    faster travel → less time to soak heat in → shallower. Those two
    directions of change are unit-tested.

KNOWN LIMITATION (per STEPS.md): Rosenthal is quasi-steady — it assumes the
torch has been moving at constant settings forever, so it is worst exactly at
stitch transitions (the lack-of-fusion moments). weld_sim.py papers over this
with a first-order thermal lag; Gate 1 tests whether that is good enough
against real sectioned coupons, with transient FEM (FEniCS) as the fallback.
"""

import math

import numpy as np

# --- Aluminium 6061 constants (SI) ---
ETA = 0.8                      # arc efficiency (GMAW on Al, typical 0.7-0.85)
K_THERMAL = 167.0              # thermal conductivity, W/(m·K)
RHO = 2700.0                   # density, kg/m^3
CP = 896.0                     # specific heat, J/(kg·K)
ALPHA = K_THERMAL / (RHO * CP)  # thermal diffusivity, m^2/s (~6.9e-5)
T_MELT_C = 652.0               # solidus/melt, °C

_MAX_DEPTH_M = 0.1             # bisection upper bound (10 cm — beyond any weld)


class GoldakHeatSource:
    """
    Double-ellipsoid volumetric heat source (Goldak 1984).

    Semi-axes: a (half-width, y), b (depth, z), c_f/c_r (front/rear lengths
    along travel, x). f_f + f_r = 2 by convention so the two half-ellipsoids
    integrate to the full absorbed power.
    """

    def __init__(self, a: float = 0.004, b: float = 0.004,
                 c_f: float = 0.004, c_r: float = 0.008,
                 f_f: float = 0.6, f_r: float = 1.4, eta: float = ETA):
        if abs((f_f + f_r) - 2.0) > 1e-9:
            raise ValueError("f_f + f_r must equal 2 (Goldak convention)")
        self.a, self.b, self.c_f, self.c_r = a, b, c_f, c_r
        self.f_f, self.f_r, self.eta = f_f, f_r, eta

    def power_density(self, x, y, z, t, V: float, I: float, v: float):
        """
        W/m^3 at lab-frame position (x, y, z) and time t, torch moving along
        +x at speed v (m/s). Vectorised over x/y/z arrays.
        """
        Q = self.eta * V * I
        xi = np.asarray(x, dtype=float) - v * t   # torch-frame coordinate
        y = np.asarray(y, dtype=float)
        z = np.asarray(z, dtype=float)
        front = xi >= 0
        c = np.where(front, self.c_f, self.c_r)
        f = np.where(front, self.f_f, self.f_r)
        coeff = (6.0 * math.sqrt(3.0) * f * Q) / (self.a * self.b * c * math.pi ** 1.5)
        return coeff * np.exp(-3.0 * xi ** 2 / c ** 2
                              - 3.0 * y ** 2 / self.a ** 2
                              - 3.0 * z ** 2 / self.b ** 2)


def fusion_zone_depth(V: float, I: float, travel_speed_mm_per_min: float,
                      ambient_c: float = 25.0, eta: float = ETA,
                      angle_factor: float = 1.0) -> float:
    """
    Quasi-steady fusion depth in METERS below a moving point source
    (Rosenthal thick-plate). angle_factor in (0, 1] scales effective power
    for off-angle torch positions. Returns 0.0 when nothing melts.
    """
    Q = eta * V * I * angle_factor
    if Q <= 0.0:
        return 0.0
    v = max(travel_speed_mm_per_min, 0.0) / 1000.0 / 60.0  # m/s
    dT_melt = T_MELT_C - ambient_c

    def excess(r: float) -> float:
        # temperature rise at depth r minus the rise needed to melt
        return Q / (2.0 * math.pi * K_THERMAL * r) * math.exp(-v * r / (2.0 * ALPHA)) - dT_melt

    lo, hi = 1e-6, _MAX_DEPTH_M
    if excess(lo) <= 0.0:      # too cold to melt even at the surface
        return 0.0
    if excess(hi) >= 0.0:      # absurd power; cap rather than diverge
        return hi
    for _ in range(80):        # bisection: excess() is monotone decreasing in r
        mid = 0.5 * (lo + hi)
        if excess(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
