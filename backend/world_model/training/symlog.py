"""
symlog.py provides the scale-taming primitives Step 8's losses are built from — symlog/symexp compression on every reconstruction target, the free-nats KL floor, and PercentileNorm for the quality loss (STEPS.md Step 8, after DreamerV3).

For newcomers — why each primitive exists:
  symlog/symexp — the recon targets live on wildly different scales (volts ~20,
    amps ~180, angles ~15, depth in mm). Squared error on raw values lets the
    biggest channel bully the loss. symlog(x) = sign(x)·log(1+|x|) compresses
    large magnitudes while staying ~identity near zero, and symexp inverts it —
    so the model PREDICTS in symlog space and consumers symexp back to real
    units. Applied to ALL recon targets so no head dominates by unit choice.
  free-nats KL — the KL term pulls the encoder posterior toward N(0,1). Left
    unchecked early in training it collapses the posterior before the decoder
    has learned to use z0 ("posterior collapse"). Flooring the KL at 1 nat
    removes the gradient below the floor: the encoder keeps at least that much
    information for free. Fixed prior, NO KL balancing (locked in the plan).
  PercentileNorm — the quality cross-entropy arrives at a different (and
    drifting) scale than the recon MSEs. Dividing by a running 5th–95th
    percentile range of its own recent values keeps its contribution O(1)
    without hand-tuning a weight per dataset. max(range, 1) so small losses
    are never amplified — this only ever scales DOWN.
"""

from collections import deque

import torch

FREE_NATS = 1.0


def symlog(x: torch.Tensor) -> torch.Tensor:
    return torch.sign(x) * torch.log1p(x.abs())


def symexp(x: torch.Tensor) -> torch.Tensor:
    return torch.sign(x) * torch.expm1(x.abs())


def free_nats_kl(mu: torch.Tensor, log_sigma: torch.Tensor,
                 free_nats: float = FREE_NATS) -> torch.Tensor:
    """
    KL( N(mu, sigma) || N(0, I) ) per sample (summed over latent dims), mean
    over the batch, floored at `free_nats`: below the floor the clamp kills
    the gradient, so the posterior is never squeezed tighter than 1 nat.
    """
    kl = 0.5 * (mu.pow(2) + (2 * log_sigma).exp() - 2 * log_sigma - 1).sum(dim=-1)
    return kl.clamp(min=free_nats).mean()


class PercentileNorm:
    """
    Running 5th–95th percentile normaliser for a scalar loss stream.

    call(value) records the raw value and returns value / max(p95 − p5, 1)
    over the most recent `window` values — scale-down only, never amplify.
    The returned tensor keeps value's gradient; only the scale is detached.
    """

    def __init__(self, window: int = 100, lo: float = 0.05, hi: float = 0.95):
        self.lo, self.hi = lo, hi
        self.values: deque[float] = deque(maxlen=window)

    def __call__(self, value: torch.Tensor) -> torch.Tensor:
        self.values.append(float(value.detach()))
        v = torch.tensor(sorted(self.values))
        scale = float(torch.quantile(v, self.hi) - torch.quantile(v, self.lo))
        return value / max(scale, 1.0)
