"""
odefunc.py defines the CONTROLLED latent dynamics dz/dt = f_θ(z, u(t), t) — the heart of the world model — plus the physics residual that grounds z_phys (STEPS.md Step 7, D6).

⚠ CONTROLLED, not autonomous. The plan docs originally wrote dz/dt = f_θ(z, t);
that is wrong for welding: the dynamics are DRIVEN by what the welder does
(volts, amps, angles, travel speed). An autonomous ODE would force z0 to
memorise the entire future input sequence, and counterfactuals ("correct the
angle at second 7") would be architecturally impossible — you cannot intervene
on an input the dynamics never receives. u(t) is exactly what the Gate 2
counterfactual explorer edits (Step 12): edit the control buffer, re-integrate
the SAME z0, compare depth curves.

For newcomers — what an ODE has to do with welding:
  The encoder compresses the observed session into one 32-number state z0
  ("the condition of the weld at t=0"). This file answers: how does that state
  EVOLVE? Instead of a step-by-step update rule (like a GRU), we learn the
  instantaneous rate of change f_θ: given the current state z and what the
  welder is currently doing u(t), how fast is each of the 32 numbers moving?
  An ODE solver (torchdiffeq) then integrates that rate forward through time
  to produce the state trajectory z(t) the decoder reads.

  u(t) is a piecewise-linear interpolation of the 5 control channels — the
  solver evaluates f at arbitrary times between frames, so the controls must
  be defined between frames too. It is a frozen buffer per session: gradients
  do not flow into it (the controls are facts about what happened, not things
  the model predicts).

  physics_residual() is the D6 grounding pressure: on the first 4 latent dims
  (z_phys) the learned rate must match a crude heat balance — heating power in,
  Newtonian cooling out. The constants come from the simulator and are
  placeholders until Gate 1 calibration fits them against sectioned coupons —
  L_physics is well-defined but physically meaningless before Gate 1.

Solver choice (both from torchdiffeq):
  odeint_adjoint + dopri5 for training — backprop through ~1500 solver steps
  stores every intermediate and blows up memory; the adjoint method instead
  re-integrates backwards, trading compute for O(1) memory.
  odeint + rk4 for inference — fixed-step, predictable latency (500 ms p95
  budget, Gate 6), no adjoint machinery needed without gradients.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchdiffeq import odeint, odeint_adjoint

from world_model.config import CONTROL_CHANNELS, LATENT_DIM, PHYS_DIMS
from world_model.simulator.weld_sim import C_THERMAL_J_PER_K, K_COOLING_PER_S

N_CONTROLS = len(CONTROL_CHANNELS)
ARC_EFFICIENCY = 0.8  # eta — same GMAW transfer efficiency the Goldak source uses

# Training-grade solver tolerances. torchdiffeq's defaults (rtol 1e-7 / atol
# 1e-9) are publication-grade and ~20× slower; at 1e-4/1e-5 the trajectory
# agrees to 4 decimals while a T=500 adjoint batch drops from ~85 s to ~4.5 s
# on CPU (measured, Step 8). Inside SGD noise, far outside the latency budget.
RTOL, ATOL = 1e-4, 1e-5


class ControlSignal:
    """
    Piecewise-linear u(t) over the 5 control channels — frozen per session.

    Holds controls [B, T, 5] on a uniform time grid t_grid [T] and returns the
    interpolated [B, 5] at any scalar t the solver asks for (clamped to the
    ends outside the grid). Detached: controls are observed facts; no gradient
    flows into them. This buffer is the counterfactual editing surface —
    Step 12 builds an edited ControlSignal and re-integrates the same z0.
    """

    def __init__(self, controls: torch.Tensor, t_grid: torch.Tensor):
        if controls.ndim != 3 or controls.shape[2] != N_CONTROLS:
            raise ValueError(f"controls must be [B, T, {N_CONTROLS}], got {tuple(controls.shape)}")
        if t_grid.ndim != 1 or t_grid.shape[0] != controls.shape[1]:
            raise ValueError("t_grid must be [T] matching controls")
        self.controls = controls.detach()
        self.t_grid = t_grid.detach()

    def __call__(self, t: torch.Tensor) -> torch.Tensor:
        T = self.controls.shape[1]
        if T == 1:
            return self.controls[:, 0]
        # uniform grid → index arithmetic instead of searchsorted
        dt = self.t_grid[1] - self.t_grid[0]
        s = ((t - self.t_grid[0]) / dt).clamp(0.0, T - 1.0)
        i0 = s.floor().long().clamp(max=T - 2)
        w = (s - i0.to(s.dtype)).clamp(0.0, 1.0)
        return torch.lerp(self.controls[:, i0], self.controls[:, i0 + 1], w)


class ControlledODEFunc(nn.Module):
    """dz/dt = f_θ(z, u(t), t): MLP(32 + 5 → 64 → 64 → 32, tanh)."""

    def __init__(self, latent_dim: int = LATENT_DIM, hidden_dim: int = 64):
        super().__init__()
        self.latent_dim = latent_dim
        self.net = nn.Sequential(
            nn.Linear(latent_dim + N_CONTROLS, hidden_dim), nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim), nn.Tanh(),
            nn.Linear(hidden_dim, latent_dim),
        )
        self._control: ControlSignal | None = None  # bound per batch, not a parameter

    def bind_control(self, control: ControlSignal) -> None:
        """Attach this batch's u(t) before integrating (torchdiffeq's f(t, z)
        signature has no room for extra arguments)."""
        self._control = control

    def rate(self, z: torch.Tensor, u: torch.Tensor) -> torch.Tensor:
        """f_θ at explicit (z, u) pairs — used by physics_residual on [B, T, ·]."""
        return self.net(torch.cat([z, u], dim=-1))

    def forward(self, t: torch.Tensor, z: torch.Tensor) -> torch.Tensor:
        if self._control is None:
            raise RuntimeError("bind_control() before integrating — the ODE is controlled")
        return self.rate(z, self._control(t))


def integrate(odefunc: ControlledODEFunc, z0: torch.Tensor, t_grid: torch.Tensor,
              control: ControlSignal, adjoint: bool) -> torch.Tensor:
    """
    Integrate z0 [B, D] through the controlled dynamics → trajectory [B, T, D].
    adjoint=True (training): odeint_adjoint + dopri5, O(1) memory.
    adjoint=False (inference): odeint + rk4, fixed cost for the latency budget.
    """
    odefunc.bind_control(control)
    if adjoint:
        z = odeint_adjoint(odefunc, z0, t_grid, method="dopri5",
                           rtol=RTOL, atol=ATOL,
                           adjoint_params=tuple(odefunc.parameters()))
    else:
        z = odeint(odefunc, z0, t_grid, method="rk4")
    return z.transpose(0, 1)  # [T, B, D] → [B, T, D]


def physics_residual(odefunc: ControlledODEFunc, z_traj: torch.Tensor,
                     control: ControlSignal) -> torch.Tensor:
    """
    D6 grounding on z_phys ONLY: at every trajectory point, the learned rate on
    z[:, :4] must match a lumped heat balance —
        dz_phys/dt ≈ η·V·I / C_THERMAL − K_COOLING · z_phys
    (power in over thermal mass, Newtonian cooling out). Evaluated at the
    solver's own output points; the free dims z[4:] carry no physics pressure.
    C_THERMAL / K_COOLING are the simulator placeholders until Gate 1 fits them.
    """
    u = control.controls.to(z_traj.dtype)                   # [B, T, 5] on the same grid
    dz_learned = odefunc.rate(z_traj, u)[..., :PHYS_DIMS]   # [B, T, 4]
    volts, amps = u[..., 0], u[..., 1]
    power = (ARC_EFFICIENCY * volts * amps / C_THERMAL_J_PER_K).unsqueeze(-1)
    dz_target = power - K_COOLING_PER_S * z_traj[..., :PHYS_DIMS]
    return F.mse_loss(dz_learned, dz_target)
