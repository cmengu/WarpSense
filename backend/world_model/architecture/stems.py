"""
stems.py turns each frame's raw 6-channel sensor values (respecting which channels are present) into a single fixed 16-dimensional embedding per timestep, using a separate small conv network per channel and averaging only over available sensors.

Shared between the GRU baseline and the world-model encoder (STEPS.md Step 3/7, D3/D5)
so Gate 3 compares dynamics models, not input pipelines.

Design points:
- One Conv1d stem PER channel, keyed by channel NAME in a ModuleDict. This is
  what makes Polito transfer (D5) work: a Polito session activates only the
  "volts" and "amps" stems, and exactly those weights warm-start later.
- Aggregation is the MEAN over channels present at each frame, NOT the sum —
  a sum makes the embedding magnitude scale with sensor count, so a 2-channel
  Polito session and a 6-channel ESP32 session would look wildly different to
  the trunk. Frames with zero available channels get a zero embedding (guard).
- Random channel dropout (D3): training drops whole channels per sample so
  masked channels are native to the model, not a special case at test time.

For newcomers — what a "stem" is and what the shapes mean:
  A neural net can't do much with 6 raw sensor numbers per frame, and some may
  be missing. Each channel gets its own tiny Conv1d "stem": a window sliding
  over 5 consecutive frames of that ONE sensor, emitting 16 numbers per frame
  that describe the local pattern (rising? spiking? flat? — the 16 features
  are learned, not hand-named). So one channel becomes a [T, 16] matrix.

  The 6 per-channel outputs are then combined frame-by-frame with a MEAN over
  the channels the mask says are present: at each frame, average the available
  16-vectors into one 16-vector. Output stays [T, 16] — one embedding per
  frame describing all sensors together (batched: [B, T, 16]).

  random_channel_dropout hides whole channels at random during training (each
  channel, prob p per sample) so "sensor missing" is a situation the model has
  seen thousands of times, not a surprise at deployment. Whole channels — not
  random frames — because that's how sensors really fail: absent for the
  session, not flickering.
"""

import torch
import torch.nn as nn

from world_model.config import CHANNELS

STEM_DIM = 16


class ChannelStems(nn.Module):
    """[B, T, C] values + [B, T, C] mask → [B, T, STEM_DIM] fused embedding."""

    def __init__(self, channels: list[str] = CHANNELS, dim: int = STEM_DIM):
        super().__init__()
        self.channels = list(channels)
        self.dim = dim
        self.stems = nn.ModuleDict({
            name: nn.Conv1d(1, dim, kernel_size=5, padding=2) for name in self.channels
        })

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        B, T, C = x.shape
        if C != len(self.channels):
            raise ValueError(f"expected {len(self.channels)} channels, got {C}")
        maskf = mask.to(x.dtype)
        x = x * maskf  # ensure masked entries contribute nothing even if nonzero
        total = x.new_zeros(B, T, self.dim)
        for c, name in enumerate(self.channels):
            # Conv1d wants [B, 1, T]; embed, then zero out frames where absent
            emb = self.stems[name](x[:, :, c].unsqueeze(1)).transpose(1, 2)  # [B, T, dim]
            total = total + emb * maskf[:, :, c].unsqueeze(-1)
        n_avail = maskf.sum(dim=2, keepdim=True)          # [B, T, 1]
        return total / n_avail.clamp(min=1.0)             # MEAN; n=0 frames → zeros


def random_channel_dropout(mask: torch.Tensor, p: float,
                           generator: torch.Generator | None = None) -> torch.Tensor:
    """
    Drop entire channels per sample (training only): [B, T, C] mask → new mask.
    Whole-channel (not per-frame) dropout matches the real failure mode — a
    sensor is absent for the session, not flickering frame to frame.
    """
    B, _, C = mask.shape
    keep = torch.rand(B, 1, C, device=mask.device, generator=generator) >= p
    return mask & keep
