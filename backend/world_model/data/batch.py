"""
batch.py pads variable-length SessionTensors into a torch Batch where padding frames use mask=False so models treat batch padding exactly like missing sensor data.

Pads to the longest session in the batch; padded frames get mask=False everywhere,
so models that respect the mask (all of ours) treat padding exactly like missing
data — one mechanism.

For newcomers: neural nets train on BATCHES (several sessions at once) for
speed, but a torch tensor must be rectangular — every session in the batch
needs the same length T. Sessions differ in length, so collate_sessions()
pads shorter ones with zeros up to the longest (T_max) and marks the padded
frames mask=False. Because every model here already ignores mask=False frames
(that's how missing sensors work, D3), padding needs no special handling —
the same mechanism covers both. The Batch dataclass also carries the labels
(quality class, per-frame depth when it exists) pulled out of each session's
meta dict, converted to tensors ready for loss computation.
"""

from dataclasses import dataclass

import numpy as np
import torch

from world_model.config import QUALITY_INDEX
from world_model.data.schema import SessionTensor


@dataclass
class Batch:
    x: torch.Tensor        # [B, T_max, C] float32
    mask: torch.Tensor     # [B, T_max, C] bool
    quality: torch.Tensor  # [B] long; QUALITY_INDEX or -1 when unlabelled
    depth: torch.Tensor    # [B, T_max] float32 per-frame fusion depth (Goldak)
    has_depth: torch.Tensor  # [B] bool
    session_ids: list[str]

    def to(self, device) -> "Batch":
        return Batch(self.x.to(device), self.mask.to(device), self.quality.to(device),
                     self.depth.to(device), self.has_depth.to(device), self.session_ids)


def collate_sessions(sessions: list[SessionTensor]) -> Batch:
    B = len(sessions)
    T_max = max(s.T for s in sessions)
    C = sessions[0].x.shape[1]
    x = np.zeros((B, T_max, C), dtype=np.float32)
    mask = np.zeros((B, T_max, C), dtype=bool)
    quality = np.full(B, -1, dtype=np.int64)
    depth = np.zeros((B, T_max), dtype=np.float32)
    has_depth = np.zeros(B, dtype=bool)
    for b, s in enumerate(sessions):
        x[b, :s.T] = s.x
        mask[b, :s.T] = s.mask
        label = s.meta.get("quality_class")
        if label is not None:
            quality[b] = QUALITY_INDEX[label]
        d = s.meta.get("fusion_depth_mm")
        if d is not None:
            depth[b, :s.T] = d
            has_depth[b] = True
    return Batch(
        x=torch.from_numpy(x), mask=torch.from_numpy(mask),
        quality=torch.from_numpy(quality), depth=torch.from_numpy(depth),
        has_depth=torch.from_numpy(has_depth),
        session_ids=[s.session_id for s in sessions],
    )
