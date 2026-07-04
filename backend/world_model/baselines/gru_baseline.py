"""
gru_baseline.py is a simple stems→GRU→quality/depth model that serves as the Gate 3 opponent — if the world model cannot beat it on macro-F1 and fusion MAE, we ship this instead (STEPS.md Step 3).

Architecture: shared per-channel stems (architecture/stems.py — identical to
the world model's, so Gate 3 compares dynamics models, not input pipelines)
→ GRU trunk → last hidden state h_T → two heads:
  quality logits (3)      — trained wherever quality labels exist
  depth_mm (scalar, h_T)  — trained only when depth labels exist (Goldak corpus)

Input normalization lives IN the model as buffers (fit_normalizer on the train
split, masked entries excluded), so checkpoints are self-contained and eval
can never accidentally use different statistics than training did. Polito data
is pre-normalised [0,1] and gets its own fit — never reuse stats across
corpora (STEPS.md Step 1 warning).

For newcomers — why a deliberately ordinary model, and how it works:
  Step 3 is "build the bar first". The world model (Steps 7–8) is only worth
  its complexity if it beats something simple, so this file IS the something
  simple: plain supervised ML, session in → answer out. If the world model
  can't beat it at Gate 3, we ship this instead.

  How it reads a session:
  - stems (architecture/stems.py) turn the raw [T, 6] sensors into one 16-dim
    embedding per frame.
  - A GRU (Gated Recurrent Unit — the workhorse recurrent net) walks the
    sequence frame by frame, carrying a 64-number "memory" it updates at each
    step: new_memory = learned_blend(old_memory, current_frame). After the
    last frame, that memory h_T summarises the whole weld.
  - Two "heads" (small final layers) read h_T: quality (3 class scores) and
    fusion depth in mm (trained only once depth labels exist — the Goldak
    simulator corpus; mock data has none).

  Contrast with the world model: this net learns only the input→label mapping
  (discriminative). It has no internal state of the weld and no dynamics, so
  it cannot predict per-frame depth curves or answer counterfactuals ("what if
  the angle was corrected at second 7?"). That extra capability is exactly
  what the world model must convert into better numbers to justify existing.

  Normalisation note: sensor channels live on wildly different scales (~20 V
  vs ~200 mm/min), which trains badly, so each channel is standardised. The
  mean/std are fit on the TRAIN split only (no test leakage) and stored inside
  the checkpoint as buffers, so eval can never use mismatched statistics.
"""

import torch
import torch.nn as nn

from world_model.config import CHANNELS, QUALITY_CLASSES
from world_model.architecture.stems import STEM_DIM, ChannelStems
from world_model.data.batch import Batch, collate_sessions
from world_model.data.schema import SessionTensor

HIDDEN_DIM = 64


class GRUBaseline(nn.Module):
    def __init__(self, channels: list[str] = CHANNELS, hidden_dim: int = HIDDEN_DIM):
        super().__init__()
        self.stems = ChannelStems(channels)
        self.trunk = nn.GRU(STEM_DIM, hidden_dim, batch_first=True)
        self.quality_head = nn.Linear(hidden_dim, len(QUALITY_CLASSES))
        self.depth_head = nn.Linear(hidden_dim, 1)
        n = len(channels)
        self.register_buffer("norm_mean", torch.zeros(n))
        self.register_buffer("norm_std", torch.ones(n))

    @torch.no_grad()
    def fit_normalizer(self, train_sessions: list[SessionTensor]) -> None:
        """Masked per-channel mean/std over the TRAIN split only (no test leakage)."""
        batch = collate_sessions(train_sessions)
        x, mask = batch.x, batch.mask
        for c in range(x.shape[2]):
            vals = x[:, :, c][mask[:, :, c]]
            if vals.numel() > 1:
                self.norm_mean[c] = vals.mean()
                self.norm_std[c] = vals.std().clamp(min=1e-6)

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> dict[str, torch.Tensor]:
        x = (x - self.norm_mean) / self.norm_std
        h = self.stems(x, mask)              # [B, T, STEM_DIM]
        out, _ = self.trunk(h)               # [B, T, HIDDEN]
        h_T = out[:, -1]                     # last hidden state
        return {
            "quality_logits": self.quality_head(h_T),   # [B, 3]
            "depth_mm": self.depth_head(h_T).squeeze(-1),  # [B]
        }

    @torch.no_grad()
    def predict(self, batch: Batch) -> dict[str, torch.Tensor]:
        """Eval-harness protocol (shared with WeldWorldModel later)."""
        self.eval()
        out = self(batch.x, batch.mask)
        return {
            "quality_probs": out["quality_logits"].softmax(dim=-1),
            "depth_mm": out["depth_mm"],
        }
