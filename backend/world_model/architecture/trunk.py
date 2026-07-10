"""
trunk.py is the shared sensor encoder — per-channel stems + a GRU trunk — that every
self-supervised pretraining objective trains and every downstream consumer warm-starts
from (STEPS.md Step 6/7, D5).

Extracted from training/pretrain_polito.py so that pretraining objectives are
siblings sharing one encoder, not each carrying a private copy: masked
reconstruction (pretraining/masked_recon.py) and JEPA both train exactly this
module, and the transfer contract is defined ONCE, here.

The transfer contract (what warm-starts Step 7/8):
  - state-dict keys are "stems.*" and "trunk.*" — these exact names appear in
    saved checkpoints (e.g. polito_pretrain_8a68998bf644.pt) and in the
    encoder-side name map (architecture/encoder.py _TRUNK_TO_CELL), so this
    class keeps `self.stems` / `self.trunk` as attribute names. Renaming them
    silently orphans every existing checkpoint.
  - the trunk is a single-layer nn.GRU: its weight_ih_l0 / weight_hh_l0 /
    bias_* are shape-identical to nn.GRUCell's weight_ih / weight_hh / bias_*,
    which is what lets the Step 7 ODE-RNN encoder cell load it by name-mapping.
  - HIDDEN_DIM here is the canonical value; architecture/encoder.py must match.

Objective-specific heads (reconstruction, fault, JEPA predictor, ...) do NOT
live here — objectives subclass or wrap this and add their own. Subclassing
keeps parameter names and RNG creation order identical to the pre-refactor
PolitoPretrainModel, which is what makes old checkpoints load bit-for-bit.
"""

import torch
import torch.nn as nn

from world_model.architecture.stems import STEM_DIM, ChannelStems

HIDDEN_DIM = 64  # transfer contract: must match architecture/encoder.py

TRANSFER_PREFIXES = ("stems.", "trunk.")


class StemTrunkEncoder(nn.Module):
    """[B, T, C] values + [B, T, C] mask → [B, T, HIDDEN_DIM] hidden states."""

    def __init__(self, channels: list[str], hidden_dim: int = HIDDEN_DIM):
        super().__init__()
        self.channels = list(channels)
        self.hidden_dim = hidden_dim
        self.stems = ChannelStems(self.channels)
        self.trunk = nn.GRU(STEM_DIM, hidden_dim, batch_first=True)

    def encode(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """Per-frame hidden states [B, T, HIDDEN_DIM]; last frame = summary."""
        h = self.stems(x, mask)      # [B, T, STEM_DIM]
        out, _ = self.trunk(h)       # [B, T, HIDDEN_DIM]
        return out

    forward = encode

    def transfer_state_dict(self) -> dict[str, torch.Tensor]:
        """The warm-start artifact: stems + trunk only, heads (if any) excluded."""
        return {k: v.clone() for k, v in self.state_dict().items()
                if k.startswith(TRANSFER_PREFIXES)}

    def load_transfer_state_dict(self, transfer_state_dict: dict[str, torch.Tensor]) -> None:
        """Warm-start stems + trunk from another encoder's transfer artifact."""
        own = {k for k in self.state_dict() if k.startswith(TRANSFER_PREFIXES)}
        missing = own - set(transfer_state_dict)
        if missing:
            raise KeyError(f"transfer artifact missing keys: {sorted(missing)}")
        self.load_state_dict(transfer_state_dict, strict=False)
