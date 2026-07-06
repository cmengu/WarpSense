"""
decoder.py reads the latent trajectory z(t) back out into observable quantities through five heads — and hard-wires the D6 grounding: the heat-dissipation head's input tensor is literally z[:, :, :4] (STEPS.md Step 7).

For newcomers — why decoding is what gives the latent meaning:
  The 32 latent numbers mean nothing by themselves; they mean whatever the
  decoder is forced to extract from them. Five heads apply that pressure:

  heat_diss_hat [B,T]  from z_phys ONLY (z[:, :, :4]). THE GROUNDING: heat
                       dissipation is the one sensed channel that is a thermal
                       consequence rather than a welder choice, and only the
                       4 physics dims may explain it. Combined with the
                       physics residual on the same dims (odefunc.py), this
                       pins z_phys to "thermal state" instead of letting the
                       network smear it anywhere. A test asserts the input
                       dim is 4 so the wiring cannot silently regress.
  other5_hat   [B,T,5] the 5 control channels from full z — reconstruction
                       pressure that makes the trajectory track the session.
  depth_hat    [B,T]   per-frame fusion depth — the timeline curve the UI
                       eventually shows (mm allowed only after Gate 5).
  quality_probs [B,3]  from concat(z_T, feats_11) — PHOENIX fusion: the final
                       latent state plus the 11 engineered features the
                       existing extractor already computes (reuse, don't
                       reimplement). Logits here; softmax at the infer surface.
  feats_hat    [B,11]  predict those same 11 features from z_T — free
                       supervision (L_aux, Step 8) from labels that cost
                       nothing to produce.
"""

import torch
import torch.nn as nn

from world_model.config import LATENT_DIM, N_FEATURES, PHYS_DIMS, QUALITY_CLASSES

DECODER_HIDDEN = 64
N_OTHER = 5  # the 5 control channels reconstructed by other5_hat


def _mlp(in_dim: int, out_dim: int, hidden: int = DECODER_HIDDEN) -> nn.Sequential:
    return nn.Sequential(nn.Linear(in_dim, hidden), nn.Tanh(), nn.Linear(hidden, out_dim))


class WorldModelDecoder(nn.Module):
    def __init__(self, latent_dim: int = LATENT_DIM, phys_dims: int = PHYS_DIMS):
        super().__init__()
        self.phys_dims = phys_dims
        self.heat_head = _mlp(phys_dims, 1)                     # z_phys ONLY (D6)
        self.sens_head = _mlp(latent_dim, N_OTHER)
        self.depth_head = _mlp(latent_dim, 1)
        self.quality_head = _mlp(latent_dim + N_FEATURES, len(QUALITY_CLASSES))
        self.feats_head = _mlp(latent_dim, N_FEATURES)

    def forward(self, z_traj: torch.Tensor,
                feats: torch.Tensor | None = None) -> dict[str, torch.Tensor]:
        """z_traj [B, T, LATENT]; feats [B, N_FEATURES] or None (→ zeros: the
        quality head degrades to latent-only rather than failing)."""
        B = z_traj.shape[0]
        z_T = z_traj[:, -1]
        if feats is None:
            feats = z_traj.new_zeros(B, N_FEATURES)
        return {
            # input tensor is literally z[:, :, :4] — the grounding (D6)
            "heat_diss_hat": self.heat_head(z_traj[:, :, :self.phys_dims]).squeeze(-1),
            "other5_hat": self.sens_head(z_traj),
            "depth_hat": self.depth_head(z_traj).squeeze(-1),
            "quality_logits": self.quality_head(torch.cat([z_T, feats], dim=-1)),
            "feats_hat": self.feats_head(z_T),
        }
