"""
losses.py computes the five world-model loss terms and blends them on the pre-registered fade-in schedule — recon always on, aux early, physics mid, quality late (STEPS.md Step 8).

For newcomers — why a SCHEDULE instead of fixed weights:
  The five pressures pull the latent in different directions, and order
  matters. Reconstruction must come first: until the trajectory tracks the
  session at all, the physics residual is regularising noise and the quality
  head is classifying garbage. So recon (+ a light aux ramp — the 11 features
  are cheap, well-scaled targets) shapes the latent from epoch 0; physics
  fades in once trajectories exist to be grounded; quality fades in LAST so
  the classifier reads a formed state instead of warping it around 3 labels.
  fade() is a smooth sigmoid ramp, not a step — no loss-surface cliff at the
  switch-on epoch. The breakpoints are written for the full 300-epoch run
  (Step 11); shorter runs pass schedule_scale = epochs/300 so the shape (and
  the relative ordering) is preserved.

The five terms (weights per the locked plan):
  recon    masked MSE in symlog space: heat_diss_hat vs the sensed heat channel,
           other5_hat vs the 5 control channels, depth_hat vs per-frame depth
           when the corpus has it (Goldak; mock does not). Always on, weight 1.
  physics  the D6 residual (odefunc.physics_residual) on z_phys — ×0.10,
           fade epochs 50→150.
  quality  class-weighted cross-entropy on labelled sessions, PercentileNorm'd
           (symlog.py) — ×1.0, fade 150→250.
  aux      feats_hat vs the 11 engineered features, symlog space — ×0.05,
           fade 0→100. Free supervision from the existing extractor.
  kl       free-nats KL of q(z0) against the fixed N(0,1) prior — ×0.001.

Targets use the ORIGINAL sensor mask, not the channel-dropout mask the model
saw: reconstructing a hidden channel from the others is precisely the
pressure that makes dropout training work.
"""

import math
from dataclasses import dataclass

import torch
import torch.nn.functional as F

from world_model.architecture.odefunc import physics_residual
from world_model.config import CHANNEL_INDEX, CONTROL_CHANNELS
from world_model.data.batch import Batch
from world_model.training.symlog import free_nats_kl, symlog

HEAT_COL = CHANNEL_INDEX["heat_dissipation_rate_celsius_per_sec"]
N_CTRL = len(CONTROL_CHANNELS)

# (weight, fade_start, fade_end) per the locked Step 8 schedule
SCHEDULE = dict(
    physics=(0.10, 50, 150),
    quality=(1.00, 150, 250),
    aux=(0.05, 0, 100),
)
KL_WEIGHT = 0.001


@dataclass
class LossTerms:
    recon: torch.Tensor
    physics: torch.Tensor
    quality: torch.Tensor
    aux: torch.Tensor
    kl: torch.Tensor

    def detached(self) -> dict[str, float]:
        return {k: float(v.detach()) for k, v in vars(self).items()}


def fade(epoch: float, start: float, end: float) -> float:
    """Sigmoid ramp 0→1 across [start, end] (≈0.002 at start, ≈0.998 at end)."""
    x = (epoch - start) / max(end - start, 1e-9)
    return 1.0 / (1.0 + math.exp(-12.0 * (x - 0.5)))


def _masked_mse(pred: torch.Tensor, target: torch.Tensor,
                mask: torch.Tensor) -> torch.Tensor:
    if not mask.any():
        return pred.new_zeros(())
    return F.mse_loss(pred[mask], target[mask])


def compute_losses(model, out: dict[str, torch.Tensor], batch: Batch,
                   target_mask: torch.Tensor,
                   feats_target: torch.Tensor | None = None,
                   feats_valid: torch.Tensor | None = None,
                   class_weights: torch.Tensor | None = None) -> LossTerms:
    """
    model: WeldWorldModel (its norm buffers define target space; its odefunc is
    where the physics residual lands). out: model(batch.x, dropped_mask, ...).
    target_mask: the PRE-dropout sensor mask [B, T, C].
    feats_target [B, 11] + feats_valid [B]: the engineered-feature targets
    (train.py computes them once per session; sessions the extractor rejects
    get valid=False and contribute nothing).
    """
    xn = (batch.x - model.norm_mean) / model.norm_std  # target space = model input space

    recon = (
        _masked_mse(out["heat_diss_hat"], symlog(xn[:, :, HEAT_COL]),
                    target_mask[:, :, HEAT_COL])
        + _masked_mse(out["other5_hat"], symlog(xn[:, :, :N_CTRL]),
                      target_mask[:, :, :N_CTRL])
    )
    if batch.has_depth.any():
        frame_valid = target_mask.any(dim=-1) & batch.has_depth.unsqueeze(-1)
        recon = recon + _masked_mse(out["depth_hat"], symlog(batch.depth), frame_valid)

    labelled = batch.quality >= 0
    quality = (F.cross_entropy(out["quality_logits"][labelled],
                               batch.quality[labelled], weight=class_weights)
               if labelled.any() else batch.x.new_zeros(()))

    if feats_target is not None and feats_valid is not None and feats_valid.any():
        aux = F.mse_loss(out["feats_hat"][feats_valid],
                         symlog(feats_target[feats_valid]))
    else:
        aux = batch.x.new_zeros(())

    return LossTerms(
        recon=recon,
        physics=physics_residual(model.odefunc, out["z_traj"], out["control"]),
        quality=quality,
        aux=aux,
        kl=free_nats_kl(out["mu0"], out["log_sigma0"]),
    )


def total_loss(L: LossTerms, epoch: int, quality_norm=None,
               schedule_scale: float = 1.0) -> torch.Tensor:
    """The locked Step 8 blend. quality_norm: a PercentileNorm instance (or
    None to skip normalisation, e.g. in tests)."""
    def w(name: str) -> float:
        weight, start, end = SCHEDULE[name]
        return weight * fade(epoch, start * schedule_scale, end * schedule_scale)

    quality = quality_norm(L.quality) if quality_norm is not None else L.quality
    return (L.recon
            + w("physics") * L.physics
            + w("quality") * quality
            + w("aux") * L.aux
            + KL_WEIGHT * L.kl)
