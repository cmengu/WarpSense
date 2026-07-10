"""
encoder.py compresses a session's stem embeddings into the initial latent state z0 via a BACKWARD ODE-RNN, and can warm-start its GRU cell from the Step 6 Polito trunk (STEPS.md Step 7, D5/D6).

Backward, because z0 must describe the weld at t=0 *informed by everything that
followed* — running last-frame-first means the final hidden state h_0 has seen
the whole session by the time it reaches the start. The controlled ODE
(odefunc.py) then re-integrates FORWARD from z0, and the decoder must
reconstruct the session from that trajectory: encode backward, explain forward.

For newcomers — the ODE-RNN recipe (Rubanova et al.) and why the pieces exist:
  A plain GRU pretends nothing happens between frames. An ODE-RNN interleaves
  two updates per frame: the GRU cell absorbs the new observation (a jump),
  then a small learned ODE drifts the hidden state through the gap to the next
  frame (here one cheap Euler step — the gaps are a uniform 10 ms, so a fancy
  solver buys nothing). At h_0 a linear layer emits mu0 and log_sigma0: the
  posterior over z0. Training samples z0 = mu0 + eps·sigma (the VAE
  reparameterisation trick — sampling stays differentiable); inference uses
  mu0 directly. The KL term against a fixed prior arrives in Step 8.

Transfer (D5): the cell is nn.GRUCell(STEM_DIM, 64) precisely because the
Polito pre-trained trunk is a single-layer nn.GRU whose weight_ih_l0 /
weight_hh_l0 / bias_* are shape-identical to GRUCell's weight_ih / weight_hh /
bias_* — load_pretrained_trunk() maps the names. A Step 6 test pins the shapes.
"""

import torch
import torch.nn as nn

from world_model.architecture.stems import STEM_DIM
from world_model.architecture.trunk import HIDDEN_DIM  # transfer contract: one value
from world_model.config import LATENT_DIM

# nn.GRU (Polito trunk) parameter name → nn.GRUCell (this encoder) name
_TRUNK_TO_CELL = {
    "trunk.weight_ih_l0": "weight_ih",
    "trunk.weight_hh_l0": "weight_hh",
    "trunk.bias_ih_l0": "bias_ih",
    "trunk.bias_hh_l0": "bias_hh",
}


class ODERNNEncoder(nn.Module):
    """[B, T, STEM_DIM] embeddings → (mu0, log_sigma0), each [B, LATENT_DIM]."""

    def __init__(self, input_dim: int = STEM_DIM, hidden_dim: int = HIDDEN_DIM,
                 latent_dim: int = LATENT_DIM):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.cell = nn.GRUCell(input_dim, hidden_dim)
        self.odefunc_enc = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim), nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
        )
        self.to_z0 = nn.Linear(hidden_dim, 2 * latent_dim)

    def forward(self, h_seq: torch.Tensor, dt: float) -> tuple[torch.Tensor, torch.Tensor]:
        B, T, _ = h_seq.shape
        h = h_seq.new_zeros(B, self.hidden_dim)
        for i in reversed(range(T)):
            h = self.cell(h_seq[:, i], h)          # jump: absorb frame i
            h = h + dt * self.odefunc_enc(h)       # drift: Euler through the gap
        mu0, log_sigma0 = self.to_z0(h).chunk(2, dim=-1)
        return mu0, log_sigma0

    def sample_z0(self, mu0: torch.Tensor, log_sigma0: torch.Tensor) -> torch.Tensor:
        """Reparameterised sample in training; posterior mean at eval."""
        if self.training:
            return mu0 + torch.randn_like(mu0) * log_sigma0.exp()
        return mu0

    def load_pretrained_trunk(self, transfer_state_dict: dict[str, torch.Tensor]) -> None:
        """Warm-start the GRU cell from the Step 6 Polito transfer artifact."""
        with torch.no_grad():
            for trunk_key, cell_key in _TRUNK_TO_CELL.items():
                getattr(self.cell, cell_key).copy_(transfer_state_dict[trunk_key])
