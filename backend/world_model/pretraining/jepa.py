"""
jepa.py holds the JEPA pretraining components: an online StemTrunkEncoder (the
student), an EMA target encoder (the answer-key maker), and a small predictor
MLP — nothing is imported from outside; JEPA is a wiring pattern around our
own encoder, not a downloadable model.

The recipe (I-JEPA adapted to sensor time series; training loop lives in C4):
  1. windows.mask_contiguous hides ONE solid block of frames per window;
  2. the ONLINE encoder sees only the visible context;
  3. the PREDICTOR maps the online hidden states at the hidden frames to a
     guess of what the encoder would say there — 64 numbers in, 64 out;
  4. the TARGET encoder sees the FULL window (no gradients) and produces the
     answer key at those frames; loss = MSE(guess, answer) in latent space.
There is deliberately NO decoder: the model never reconstructs raw volts/amps,
so it spends no capacity on unpredictable signal noise.

Why the target is an EMA copy and not the online encoder itself: if one
network produced both guess and answer, "output a constant vector for
everything" would zero the loss (representation collapse). The target gets no
gradients; instead ema_update() drags it slowly behind the student
(target = decay*target + (1-decay)*online, BYOL/I-JEPA convention). The slow
drift closes the collapse shortcut.

What transfers: ONLY the online encoder's stems.* / trunk.* — JEPAPretrainModel
subclasses StemTrunkEncoder so those keys keep the contract names, and the
predictor/target live under other prefixes, so transfer_state_dict() excludes
them for free. A JEPA checkpoint saved through pretraining/common.py is
indistinguishable from a masked_recon one except for objective="jepa".
"""

import torch
import torch.nn as nn

from world_model.architecture.trunk import HIDDEN_DIM, TRANSFER_PREFIXES, StemTrunkEncoder

EMA_DECAY = 0.996
PREDICTOR_DIM = 128


class JEPAPretrainModel(StemTrunkEncoder):
    """Online encoder (= self) + predictor MLP + gradient-free EMA target."""

    def __init__(self, channels: list[str], hidden_dim: int = HIDDEN_DIM,
                 predictor_dim: int = PREDICTOR_DIM, ema_decay: float = EMA_DECAY):
        super().__init__(channels, hidden_dim)  # self.stems / self.trunk = online
        self.ema_decay = ema_decay
        self.predictor = nn.Sequential(
            nn.Linear(hidden_dim, predictor_dim),
            nn.GELU(),
            nn.Linear(predictor_dim, hidden_dim),
        )
        # target starts as an exact copy of the online encoder, then only
        # ever moves via ema_update() — never via gradients
        self.target = StemTrunkEncoder(self.channels, hidden_dim)
        self.target.load_state_dict(self._online_state())
        self.target.requires_grad_(False)

    def _online_state(self) -> dict[str, torch.Tensor]:
        """Live (non-cloned) views of the online stems+trunk tensors."""
        return {k: v for k, v in self.state_dict().items()
                if k.startswith(TRANSFER_PREFIXES)}

    def forward(self, x: torch.Tensor, input_mask: torch.Tensor) -> torch.Tensor:
        """Context view in, predicted embeddings out: [B, T, HIDDEN_DIM]."""
        return self.predictor(self.encode(x, input_mask))

    @torch.no_grad()
    def target_encode(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """Answer key: target embeddings of the FULL (unmasked) window."""
        return self.target.encode(x, mask)

    @torch.no_grad()
    def ema_update(self) -> None:
        """Drag the target behind the student: t = d*t + (1-d)*online."""
        online = self._online_state()
        for k, t in self.target.state_dict().items():
            t.mul_(self.ema_decay).add_(online[k], alpha=1.0 - self.ema_decay)
