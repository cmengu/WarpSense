"""
world_model.py assembles stems → backward ODE-RNN encoder → controlled ODE → five decoder heads into WeldWorldModel, the generative counterpart the GRU baseline must lose to at Gate 3 (STEPS.md Step 7).

Dataflow for one session (shapes for batch B, length T):
    x [B,T,6] + mask ──ChannelStems──► emb [B,T,16]
    emb ──ODERNNEncoder (backward)──► mu0, log_sigma0 ──sample──► z0 [B,32]
    x[:, :, :5] (normalised controls) ──► ControlSignal u(t)   (frozen buffer)
    z0 ──odeint(f_θ(z, u(t), t))──► z_traj [B,T,32]
    z_traj ──WorldModelDecoder──► heat/sensors/depth curves, quality, features

Unlike the GRU baseline (input → label, no internal state), this model commits
to a STATE of the weld and dynamics for how it evolves under the controls.
That buys per-frame depth curves and counterfactuals — forward(..., controls=
edited_buffer) re-integrates the same z0 under different inputs (Gate 2's
monotonicity battery, Step 12) — and must convert into better Gate 3 numbers
to justify its complexity.

Practical notes:
  - Normalisation lives in buffers exactly like the GRU baseline (fit on the
    train split, stored in the checkpoint) — eval can never use mismatched
    statistics. The control buffer u(t) uses the same normalised values, so
    the physics-residual constants are placeholders squared until Gate 1
    calibration; that is pre-registered (STEPS.md Step 7/9).
  - Solver path follows self.training: adjoint dopri5 when training (memory),
    plain rk4 at eval (latency). See odefunc.py.
  - feats_11 (quality-head fusion input) is optional here: the training loop
    (Step 8) and the service layer (Step 14, al_feature_cache) supply it;
    without it the quality head runs latent-only over zeros.
"""

import torch
import torch.nn as nn

from world_model.architecture.decoder import WorldModelDecoder
from world_model.architecture.encoder import HIDDEN_DIM, ODERNNEncoder
from world_model.architecture.odefunc import ControlledODEFunc, ControlSignal, integrate
from world_model.architecture.stems import ChannelStems
from world_model.config import CHANNELS, CONTROL_CHANNELS, LATENT_DIM, SENSOR_HZ
from world_model.data.batch import collate_sessions
from world_model.data.schema import SessionTensor


class WeldWorldModel(nn.Module):
    def __init__(self, channels: list[str] = CHANNELS, latent_dim: int = LATENT_DIM,
                 hidden_dim: int = HIDDEN_DIM):
        super().__init__()
        self.stems = ChannelStems(channels)
        self.encoder = ODERNNEncoder(hidden_dim=hidden_dim, latent_dim=latent_dim)
        self.odefunc = ControlledODEFunc(latent_dim=latent_dim)
        self.decoder = WorldModelDecoder(latent_dim=latent_dim)
        n = len(channels)
        self.register_buffer("norm_mean", torch.zeros(n))
        self.register_buffer("norm_std", torch.ones(n))

    @torch.no_grad()
    def fit_normalizer(self, train_sessions: list[SessionTensor]) -> None:
        """Masked per-channel mean/std over the TRAIN split only (no test leakage)."""
        batch = collate_sessions(train_sessions)
        for c in range(batch.x.shape[2]):
            vals = batch.x[:, :, c][batch.mask[:, :, c]]
            if vals.numel() > 1:
                self.norm_mean[c] = vals.mean()
                self.norm_std[c] = vals.std().clamp(min=1e-6)

    def forward(self, x: torch.Tensor, mask: torch.Tensor,
                feats: torch.Tensor | None = None,
                controls: torch.Tensor | None = None) -> dict[str, torch.Tensor]:
        """
        x, mask [B, T, 6]; feats [B, 11] or None; controls [B, T, 5] or None.
        `controls` overrides the u(t) buffer (NORMALISED units, like x after the
        buffers) — the counterfactual hook: same session, edited inputs,
        re-integrated trajectory. z0 still encodes the observed session.
        """
        B, T, _ = x.shape
        xn = (x - self.norm_mean) / self.norm_std
        emb = self.stems(xn, mask)                                # [B, T, 16]
        dt = 1.0 / SENSOR_HZ
        mu0, log_sigma0 = self.encoder(emb, dt)
        z0 = self.encoder.sample_z0(mu0, log_sigma0)              # [B, LATENT]

        if controls is None:
            n_ctrl = len(CONTROL_CHANNELS)
            controls = xn[:, :, :n_ctrl] * mask[:, :, :n_ctrl]    # masked → 0
        t_grid = torch.arange(T, device=x.device, dtype=xn.dtype) * dt
        control = ControlSignal(controls, t_grid)

        z_traj = integrate(self.odefunc, z0, t_grid, control, adjoint=self.training)
        out = self.decoder(z_traj, feats)
        out.update(z_traj=z_traj, mu0=mu0, log_sigma0=log_sigma0, control=control)
        return out

    @torch.no_grad()
    def infer(self, session: SessionTensor,
              feats: torch.Tensor | None = None) -> dict[str, torch.Tensor]:
        """Eval-harness protocol (mirrors GRUBaseline.predict): one session in,
        per-frame curves + quality probabilities out. rk4 path (self.eval())."""
        self.eval()
        batch = collate_sessions([session])
        out = self(batch.x, batch.mask, feats=feats)
        return {
            "quality_probs": out["quality_logits"].softmax(dim=-1)[0],  # [3]
            "depth_mm": out["depth_hat"][0],                            # [T]
            "heat_diss_hat": out["heat_diss_hat"][0],                   # [T]
            "z_traj": out["z_traj"][0],                                 # [T, LATENT]
            "feats_hat": out["feats_hat"][0],                           # [11]
        }
