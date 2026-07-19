"""
windows.py slices SessionTensors into fixed-length training windows and provides the
frame-masking functions that self-supervised objectives build their puzzles from
(masked reconstruction: scattered frames; JEPA: one contiguous block).

Two dataset classes, deliberately, instead of one with a flag:

  TrainWindows  — returns (x, mask) ONLY. It has no labels field to leak, which
                  makes "self-supervised training never sees labels" a property
                  of the type, not of reviewer discipline. Pretraining loops
                  must consume this class and nothing else.
  ProbeWindows  — returns (x, mask, labels, group). Labels come from session
                  meta; group is the session index for GroupKFold — windows of
                  one session must stay in one fold (neighbouring windows
                  overlap, so a frame-level split leaks; same trap Gate 1.5
                  avoids in eval/probes.py).

For newcomers — why windows at all: sessions are minutes long and vary in
length, but SSL objectives want many fixed-size samples. A window of ~300
frames (3 s at 100 Hz) with stride 50 turns each session into dozens of
overlapping samples, exactly like eval/probes.py does for the Gate 1.5 oracle.
Sessions shorter than one window are skipped.

The two masking recipes (both: hide whole frames, all channels at once):
  mask_timesteps  — hide a scattered `fraction` of frames (the BERT recipe;
                    moved verbatim from training/pretrain_polito.py).
  mask_contiguous — hide `n_blocks` disjoint contiguous blocks totalling a
                    fraction of frames drawn from `ratio_range` (the I-JEPA
                    recipe: predicting missing REGIONS from context is harder
                    than infilling scattered single frames, which local
                    smoothness solves). n_blocks=1 is one solid block.
Both return (input_mask, hidden): input_mask is what the encoder may see,
hidden [B, T] marks the frames the objective must account for.
"""

import torch

from world_model.config import CHANNEL_INDEX
from world_model.data.schema import SessionTensor


class TrainWindows(torch.utils.data.Dataset):
    """Label-free windows for self-supervised pretraining: item = (x, mask)."""

    def __init__(self, sessions: list[SessionTensor], window: int = 300,
                 stride: int = 50, channels: list[str] | None = None):
        self.window = window
        self.channels = list(channels) if channels is not None else None
        self.cols = ([CHANNEL_INDEX[c] for c in self.channels]
                     if self.channels is not None else None)
        self.sessions = sessions
        self.index: list[tuple[int, int]] = [
            (i, start)
            for i, s in enumerate(sessions)
            for start in range(0, s.T - window + 1, stride)
        ]

    def __len__(self) -> int:
        return len(self.index)

    def __getitem__(self, item: int) -> tuple[torch.Tensor, torch.Tensor]:
        i, start = self.index[item]
        s = self.sessions[i]
        x = torch.from_numpy(s.x[start:start + self.window]).float()
        mask = torch.from_numpy(s.mask[start:start + self.window])
        if self.cols is not None:
            x, mask = x[:, self.cols], mask[:, self.cols]
        return x, mask


class ProbeWindows(TrainWindows):
    """Labelled windows for linear-probe evaluation ONLY — never for training.

    item = (x, mask, labels, group). labels holds the session meta entries
    named in label_keys (missing keys → None); group is the session index,
    ready for GroupKFold.
    """

    def __init__(self, sessions: list[SessionTensor], label_keys: list[str],
                 window: int = 300, stride: int = 50,
                 channels: list[str] | None = None):
        super().__init__(sessions, window=window, stride=stride, channels=channels)
        self.label_keys = list(label_keys)

    def __getitem__(self, item: int):
        x, mask = super().__getitem__(item)
        i, _ = self.index[item]
        meta = self.sessions[i].meta
        labels = {k: meta.get(k) for k in self.label_keys}
        return x, mask, labels, i


def stack_windows(dataset: TrainWindows, indices) -> tuple[torch.Tensor, torch.Tensor]:
    """Collate window items into (x[B,W,C], mask[B,W,C]) batch tensors."""
    items = [dataset[i] for i in indices]
    return (torch.stack([x for x, _ in items]),
            torch.stack([m for _, m in items]))


def mask_timesteps(mask: torch.Tensor, fraction: float,
                   generator: torch.Generator) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Hide `fraction` of frames (whole timesteps, all channels) from the input.
    Returns (input_mask, hidden) where hidden [B,T] marks frames to reconstruct.
    """
    B, T, _ = mask.shape
    hidden = torch.rand(B, T, generator=generator) < fraction
    input_mask = mask & ~hidden.unsqueeze(-1)
    return input_mask, hidden


def mask_contiguous(mask: torch.Tensor, ratio_range: tuple[float, float] = (0.25, 0.5),
                    generator: torch.Generator | None = None,
                    n_blocks: int = 1) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Hide `n_blocks` disjoint contiguous blocks of frames per sample (the JEPA
    target regions). The TOTAL hidden fraction of T is drawn per sample from
    ratio_range and split evenly across blocks; block b is placed uniformly
    inside its own 1/n_blocks segment of the window, with one visible frame
    reserved between segments so the blocks never touch (exactly n_blocks
    separate regions, always).

    n_blocks=1 is the original one-block recipe, draw-for-draw identical.
    Multi-block (I-JEPA uses ~4 targets) hides the same total amount in
    several places, so the model must understand the dynamics at several
    scattered regions instead of bridging one gap.
    """
    B, T, _ = mask.shape
    lo, hi = ratio_range
    frac = lo + (hi - lo) * torch.rand(B, generator=generator)
    total = (frac * T).long().clamp(min=n_blocks, max=T)
    block_len = (total // n_blocks).clamp(min=1)
    t = torch.arange(T).unsqueeze(0)                       # [1, T]
    hidden = torch.zeros(B, T, dtype=torch.bool)
    for b in range(n_blocks):
        seg_start = b * T // n_blocks
        seg_end = (b + 1) * T // n_blocks
        gap = 1 if b < n_blocks - 1 else 0     # keep neighbouring blocks apart
        length = block_len.clamp(max=seg_end - gap - seg_start)
        span = (seg_end - gap - seg_start - length + 1).float()
        start = seg_start + (torch.rand(B, generator=generator) * span).long()
        hidden |= (t >= start.unsqueeze(1)) & (t < (start + length).unsqueeze(1))
    input_mask = mask & ~hidden.unsqueeze(-1)
    return input_mask, hidden
