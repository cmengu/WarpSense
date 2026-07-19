"""
common.py defines THE transfer-checkpoint contract: every pretraining objective saves
this exact artifact, and everything downstream (Step 7 warm-start, Step 8 training,
eval/compare_pretrains) loads pretrained encoders only through here.

The contract is what makes objectives swappable: a checkpoint from
masked_recon and one from jepa are indistinguishable to consumers except for
the "objective" field. If JEPA someday wins the probe comparison, pointing
Step 8's warm-start at a JEPA checkpoint is the ENTIRE migration.

Checkpoint payload:
  transfer_state_dict — stems.* + trunk.* weights (trunk.py contract keys)
  objective           — "masked_recon" | "jepa" | "supervised_depth" | ...
                        (which recipe trained it)
  channels            — stem names, so the encoder can be rebuilt exactly
  stem_dim, hidden_dim— shape parameters, same purpose
  config              — the training config dict (hyperparams, data limits)
  ...extras           — objective-specific metrics ride along untouched

Back-compat: the Step 6 artifact (polito_pretrain_8a68998bf644.pt) predates
the "objective" field; load_transfer_checkpoint() infers "masked_recon" for
such files rather than failing, so the historical checkpoint stays first-class.
"""

from pathlib import Path

import torch

from world_model.architecture.stems import STEM_DIM
from world_model.architecture.trunk import StemTrunkEncoder

KNOWN_OBJECTIVES = ("masked_recon", "jepa", "supervised_depth")


def save_transfer_checkpoint(path: Path, encoder: StemTrunkEncoder, objective: str,
                             config: dict, extras: dict | None = None) -> None:
    """Write the contract artifact. `extras` (e.g. test metrics) ride along."""
    if objective not in KNOWN_OBJECTIVES:
        raise ValueError(f"unknown objective {objective!r}; known: {KNOWN_OBJECTIVES}")
    payload = {
        "transfer_state_dict": encoder.transfer_state_dict(),
        "objective": objective,
        "channels": encoder.channels,
        "stem_dim": STEM_DIM,
        "hidden_dim": encoder.hidden_dim,
        "config": config,
    }
    if extras:
        overlap = set(extras) & set(payload)
        if overlap:
            raise ValueError(f"extras may not shadow contract keys: {sorted(overlap)}")
        payload.update(extras)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, path)


def load_transfer_checkpoint(path: Path) -> dict:
    """Load any transfer checkpoint, old or new, into contract shape."""
    ckpt = torch.load(path, weights_only=True)
    if "transfer_state_dict" not in ckpt:
        raise KeyError(f"{path} is not a transfer checkpoint (no transfer_state_dict)")
    # pre-contract artifacts (Step 6) carry no objective field
    ckpt.setdefault("objective", "masked_recon")
    return ckpt


def build_encoder(ckpt: dict) -> StemTrunkEncoder:
    """Rebuild the pretrained encoder from a loaded checkpoint, weights loaded."""
    encoder = StemTrunkEncoder(ckpt["channels"], ckpt["hidden_dim"])
    encoder.load_transfer_state_dict(ckpt["transfer_state_dict"])
    return encoder
