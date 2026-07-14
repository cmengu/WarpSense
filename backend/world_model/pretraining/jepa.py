"""
jepa.py holds the JEPA pretraining components: an online StemTrunkEncoder (the
student), an EMA target encoder (the answer-key maker), and a small predictor
MLP — nothing is imported from outside; JEPA is a wiring pattern around our
own encoder, not a downloadable model.

The recipe (I-JEPA adapted to sensor time series):
  1. windows.mask_contiguous hides n_blocks solid blocks of frames per window
     (default 4 blocks totalling 40-50%% — the time-series literature sweet
     spot; --n-blocks 1 is the minimum-moving-parts smoke configuration);
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

CLI (from backend/):
  python -m world_model.pretraining.jepa --tiny
  python -m world_model.pretraining.jepa --epochs 30 --n-blocks 1

Training diet (C4-C7 spec, issue #18): TrainWindows window=300 stride=50 —
the SAME windows masked_recon re-trains on, so the C7 head-to-head changes
exactly one variable. EMA decay is fixed at 0.996 (no ramp).

Collapse watch: evaluate() reports embed_std (per-dim std of the target
embeddings at hidden frames) and latent_mse_mean_baseline (the loss of
predicting the average embedding everywhere). A healthy run has latent_mse
well under the baseline with embed_std comfortably away from zero; collapse
shows up as BOTH numbers racing to zero together — the loss looks great while
the encoder says the same thing about every weld.
"""

import argparse
import random

import torch
import torch.nn as nn

from world_model.architecture.trunk import HIDDEN_DIM, TRANSFER_PREFIXES, StemTrunkEncoder
from world_model.config import SEED, TINY
from world_model.data.schema import SessionTensor
from world_model.data.windows import TrainWindows, mask_contiguous, stack_windows
from world_model.pretraining.masked_recon import (
    CHECKPOINTS_DIR, PRETRAIN_CHANNELS, seed_everything)

EMA_DECAY = 0.996
PREDICTOR_DIM = 128

WINDOW = 300     # C4-C7 spec: inherited from Gate 1.5, revisited by C6
STRIDE = 50
N_BLOCKS = 4     # I-JEPA-style multi-target; 1 = one solid block (smoke config)
RATIO_RANGE = (0.40, 0.50)   # TOTAL hidden fraction, split across blocks


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


# ------------------------------------------------------------- training (C4)

def _jepa_batch_loss(model: JEPAPretrainModel, x: torch.Tensor, mask: torch.Tensor,
                     input_mask: torch.Tensor, hidden: torch.Tensor) -> torch.Tensor:
    """Latent MSE at the hidden frames — mask-agnostic: graded wherever
    `hidden` is true (one block or many), on frames with real data."""
    pred = model(x * input_mask, input_mask)
    tgt = model.target_encode(x, mask)
    sel = hidden & mask.any(dim=-1)
    if not sel.any():
        return torch.zeros((), device=x.device)
    return ((pred - tgt)[sel] ** 2).mean()


@torch.no_grad()
def evaluate(model: JEPAPretrainModel, windows: TrainWindows, batch_size: int = 64,
             seed: int = SEED, device: str = "cpu", n_blocks: int = N_BLOCKS,
             ratio_range: tuple[float, float] = RATIO_RANGE) -> dict:
    """Held-out latent MSE + the two collapse dials (see module docstring)."""
    model.eval()
    gen = torch.Generator().manual_seed(seed + 1)  # fixed eval mask, ≠ train stream
    sq = n_elem = 0.0
    dim_sum = torch.zeros(model.hidden_dim)
    dim_sumsq = torch.zeros(model.hidden_dim)
    n_frames = 0.0
    for i in range(0, len(windows), batch_size):
        x, mask = stack_windows(windows, range(i, min(i + batch_size, len(windows))))
        input_mask, hidden = mask_contiguous(mask, ratio_range, gen, n_blocks)
        x, mask = x.to(device), mask.to(device)
        input_mask, hidden = input_mask.to(device), hidden.to(device)
        pred = model(x * input_mask, input_mask)
        tgt = model.target_encode(x, mask)
        sel = hidden & mask.any(dim=-1)
        if sel.any():
            sq += float(((pred - tgt)[sel] ** 2).sum())
            n_elem += float(sel.sum()) * model.hidden_dim
            dim_sum += tgt[sel].sum(dim=0).cpu()
            dim_sumsq += (tgt[sel] ** 2).sum(dim=0).cpu()
            n_frames += float(sel.sum())
    # per-dim variance of the target embeddings at graded frames; predicting
    # the mean embedding everywhere scores exactly this variance as its MSE
    var = (dim_sumsq / max(n_frames, 1) - (dim_sum / max(n_frames, 1)) ** 2).clamp(min=0)
    return {
        "n_windows": len(windows),
        "latent_mse": sq / max(n_elem, 1),
        "latent_mse_mean_baseline": float(var.mean()),
        "embed_std": float(var.sqrt().mean()),
    }


def pretrain_jepa(train: list[SessionTensor], val: list[SessionTensor], epochs: int,
                  window: int = WINDOW, stride: int = STRIDE, batch_size: int = 64,
                  lr: float = 1e-3, n_blocks: int = N_BLOCKS,
                  ratio_range: tuple[float, float] = RATIO_RANGE,
                  ema_decay: float = EMA_DECAY, device: str = "cpu",
                  seed: int = SEED, eval_every: int = 5
                  ) -> tuple[JEPAPretrainModel, dict]:
    seed_everything(seed)
    model = JEPAPretrainModel(PRETRAIN_CHANNELS, ema_decay=ema_decay).to(device)
    optimizer = torch.optim.Adam(
        [p for p in model.parameters() if p.requires_grad], lr=lr)

    train_ds = TrainWindows(train, window=window, stride=stride, channels=PRETRAIN_CHANNELS)
    val_ds = TrainWindows(val, window=window, stride=stride, channels=PRETRAIN_CHANNELS)
    mask_gen = torch.Generator().manual_seed(seed)
    order = list(range(len(train_ds)))
    shuffle_rng = random.Random(seed)
    history = {"loss": []}
    for epoch in range(epochs):
        model.train()
        shuffle_rng.shuffle(order)
        ep_loss, n_batches = 0.0, 0
        for i in range(0, len(order), batch_size):
            x, mask = stack_windows(train_ds, order[i:i + batch_size])
            input_mask, hidden = mask_contiguous(mask, ratio_range, mask_gen, n_blocks)
            loss = _jepa_batch_loss(model, x.to(device), mask.to(device),
                                    input_mask.to(device), hidden.to(device))
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            model.ema_update()
            ep_loss += float(loss.detach()); n_batches += 1
        history["loss"].append(ep_loss / max(n_batches, 1))

        if (epoch + 1) % eval_every == 0 or epoch == epochs - 1:
            m = evaluate(model, val_ds, seed=seed, device=device,
                         n_blocks=n_blocks, ratio_range=ratio_range)
            print(f"epoch {epoch + 1:3d}  loss {history['loss'][-1]:.5f}  "
                  f"val latent MSE {m['latent_mse']:.5f} "
                  f"(mean-baseline {m['latent_mse_mean_baseline']:.5f})  "
                  f"embed std {m['embed_std']:.4f}")
    return model, history


def main():
    from world_model.data.loader_polito import load_polito_sessions
    from world_model.data.splits import split_sessions
    from world_model.eval.eval_world_model import append_run
    from world_model.pretraining.common import save_transfer_checkpoint

    p = argparse.ArgumentParser(description="JEPA pre-training on Polito (C4)")
    p.add_argument("--tiny", action="store_true", help=f"dev preset: {TINY}")
    p.add_argument("--limit", type=int, default=None, help="read only first N welds")
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--device", default="cpu", choices=["cpu", "mps", "cuda"])
    p.add_argument("--seed", type=int, default=SEED)
    p.add_argument("--window", type=int, default=WINDOW)
    p.add_argument("--stride", type=int, default=STRIDE)
    p.add_argument("--n-blocks", type=int, default=N_BLOCKS,
                   help="masked blocks per window; 1 = smoke configuration")
    p.add_argument("--ratio", type=float, nargs=2, default=list(RATIO_RANGE),
                   metavar=("LO", "HI"), help="total hidden fraction range")
    args = p.parse_args()
    limit = TINY["n_sessions"] if args.tiny else args.limit
    epochs = TINY["epochs"] if args.tiny else args.epochs
    ratio_range = tuple(args.ratio)

    print(f"loading Polito welds (limit={limit})")
    sessions = load_polito_sessions(limit=limit)
    splits = split_sessions(sessions, seed=args.seed)
    print({k: len(v) for k, v in splits.items()},
          f"window={args.window} stride={args.stride} "
          f"n_blocks={args.n_blocks} ratio={ratio_range}")

    model, history = pretrain_jepa(
        splits["train"], splits["val"], epochs=epochs, window=args.window,
        stride=args.stride, n_blocks=args.n_blocks, ratio_range=ratio_range,
        device=args.device, seed=args.seed)

    test_ds = TrainWindows(splits["test"], window=args.window, stride=args.stride,
                           channels=PRETRAIN_CHANNELS)
    m = evaluate(model, test_ds, seed=args.seed, device=args.device,
                 n_blocks=args.n_blocks, ratio_range=ratio_range)
    collapsed = m["embed_std"] < 1e-3
    print(f"TEST latent MSE {m['latent_mse']:.5f} "
          f"(mean-baseline {m['latent_mse_mean_baseline']:.5f})  "
          f"embed std {m['embed_std']:.4f}  "
          f"collapse: {'SUSPECT — constant embeddings' if collapsed else 'no'}")

    config = dict(model="jepa_pretrain", epochs=epochs, limit=limit,
                  hidden=HIDDEN_DIM, window=args.window, stride=args.stride,
                  n_blocks=args.n_blocks, ratio_range=list(ratio_range),
                  ema_decay=EMA_DECAY, seed=args.seed)
    # probe macro-F1 is C5's job — the quality column stays empty here; the
    # note field must stay comma-free (runs.csv is comma-joined)
    config_hash = append_run(
        "jepa_pretrain", config, args.seed, split="test",
        metrics=dict(n=m["n_windows"], quality_f1_macro=None,
                     fusion_mae_mm=None, per_class_recall=None),
        note=(f"jepa latent_mse={m['latent_mse']:.5f} "
              f"mean_baseline={m['latent_mse_mean_baseline']:.5f} "
              f"embed_std={m['embed_std']:.4f} "
              f"collapse={'suspect' if collapsed else 'no'}"))

    ckpt = CHECKPOINTS_DIR / f"jepa_pretrain_{config_hash}.pt"
    save_transfer_checkpoint(ckpt, model, objective="jepa", config=config,
                             extras={"test_metrics": m})
    print(f"transfer artifact: {ckpt}")


if __name__ == "__main__":
    main()
