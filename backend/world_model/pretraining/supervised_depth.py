"""
supervised_depth.py is the ODD SIBLING in pretraining/: the one objective that is
NOT self-supervised. Where masked_recon and jepa invent a puzzle out of the raw
signal (hide frames, predict them / their embedding) because the Polito era had
no labels, this arm uses a label the simulator hands over for free — the
per-frame fusion depth ground truth in meta["fusion_depth_mm"] — and regresses
it directly (C8 §4/T5, decision D4).

Why it exists (the trap it tests, T5): carrying the SSL framing forward into the
simulator era discards a stronger training signal for no stated reason. Gate 1.5
already showed supervised learning works in sim (gradient boosting hit 0.109 mm
MAE). The counter-argument for keeping SSL is real — an encoder fitted directly
to Goldak's depth mapping is maximally exposed to trap T1 (learning the
simulator's inverse rather than weld physics) — but "SSL is still right here"
should be *measured*, not assumed. This arm is the fourth contender that makes
the measurement possible.

  The pre-registered prediction (§7/TH4): supervised WINS on simulated depth
  (it trains on exactly that) and LOSES on the real Polito fault bit. Only the
  real-domain number is diagnostic — beating the SSL arms on sim proves nothing,
  because it trained on the sim target. If it wins on BOTH by the TH4 margin,
  the SSL framing is obsolete for this project.

The one rule that makes T5 readable — OBJECTIVE ONLY (D4):
  This arm must differ from masked_recon / jepa in the training objective and in
  NOTHING else. Same StemTrunkEncoder, same PRETRAIN_CHANNELS (volts, amps) — so
  the stems and trunk have identical shapes and identical transfer-state-dict
  keys, and a supervised checkpoint is interchangeable with an SSL one wherever
  pretraining/common.py loads weights. Any architectural difference (more
  channels, a bigger head, a different trunk) would confound the comparison: a
  win could then be the architecture, not the objective. The head is therefore
  the smallest thing that can turn a hidden state into a depth prediction — one
  Linear(hidden_dim, 1) — and it does NOT transfer (it lives under "depth_head.",
  outside TRANSFER_PREFIXES, so transfer_state_dict() drops it for free).

The target convention (matches training/symlog.py):
  Depth is in millimetres, a different scale from the volts/amps the recon head
  predicts, so it goes through the same symlog compression every Step 8 recon
  target uses: the model predicts symlog(depth_mm) and MSE is taken in that
  space. Consumers symexp() back to millimetres — evaluate() reports MAE in real
  mm so the number is comparable to Gate 1.5's 0.109 mm.

Corpus: goldak ONLY. Polito carries no per-frame depth label (wrong process,
2 of 6 channels), so there is nothing to supervise on there — main() refuses any
other corpus rather than silently training on absent labels.

CLI (from backend/):
  python -m world_model.pretraining.supervised_depth --tiny
  python -m world_model.pretraining.supervised_depth --epochs 30 --corpus-sessions 2000

Training diet (C8 §6, issue #24): the SAME TrainWindows diet the SSL arms use on
goldak — window=300, stride=50 — so the head-to-head changes exactly one
variable. The three-seed convergence run is on goldak-wide.
"""

import argparse
import random

import torch
import torch.nn as nn
import torch.nn.functional as F

from world_model.architecture.trunk import HIDDEN_DIM, StemTrunkEncoder
from world_model.config import SEED, TINY
from world_model.data.schema import SessionTensor
from world_model.data.windows import TrainWindows
from world_model.pretraining.masked_recon import (
    CHECKPOINTS_DIR, DEFAULT_WINDOW, PRETRAIN_CHANNELS, add_corpus_args,
    load_corpus, seed_everything)
from world_model.training.symlog import symexp, symlog

STRIDE = 50
DEPTH_KEY = "fusion_depth_mm"   # simulator ground-truth label, meta[DEPTH_KEY][T]


class SupervisedDepthModel(StemTrunkEncoder):
    """The shared stems+trunk encoder plus one supervised-only linear head.

    Subclasses StemTrunkEncoder (exactly like PolitoPretrainModel and
    JEPAPretrainModel) so the transferable parameters keep the contract names
    and the encoder is architecturally identical to the SSL arms. The only
    addition is depth_head: a single Linear(hidden_dim, 1) that maps each
    per-frame hidden state to a scalar depth prediction in symlog space. It
    lives under "depth_head.", outside TRANSFER_PREFIXES, so it never rides in
    the transfer checkpoint — the objective is the sole difference from the SSL
    arms, the head is not.
    """

    def __init__(self, channels: list[str] = PRETRAIN_CHANNELS,
                 hidden_dim: int = HIDDEN_DIM):
        super().__init__(channels, hidden_dim)
        self.depth_head = nn.Linear(hidden_dim, 1)

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """x, mask: [B, T, C] → predicted symlog-depth per frame, [B, T]."""
        out = self.encode(x, mask)             # [B, T, HIDDEN]
        return self.depth_head(out).squeeze(-1)  # [B, T]


class DepthWindows(TrainWindows):
    """TrainWindows that also yields the per-frame depth target for its slice.

    TrainWindows is deliberately label-free so SSL loops can never see a label;
    ProbeWindows already subclasses it to attach session-meta labels for eval.
    This is the training-time analogue for the ONE supervised arm: it returns
    (x, mask, depth) where depth is meta[DEPTH_KEY] sliced to the SAME window as
    x, so the per-frame targets stay aligned frame-for-frame. Window/stride
    indexing is inherited unchanged, which is what keeps the diet identical to
    the SSL arms' — only the extra return value differs.
    """

    def __init__(self, sessions: list[SessionTensor], window: int = DEFAULT_WINDOW,
                 stride: int = STRIDE, channels: list[str] | None = PRETRAIN_CHANNELS,
                 depth_key: str = DEPTH_KEY):
        super().__init__(sessions, window=window, stride=stride, channels=channels)
        self.depth_key = depth_key

    def __getitem__(self, item: int):
        x, mask = super().__getitem__(item)
        i, start = self.index[item]
        depth = self.sessions[i].meta[self.depth_key][start:start + self.window]
        return x, mask, torch.from_numpy(depth).float()


def stack_depth_windows(dataset: DepthWindows, indices
                        ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Collate depth-window items into (x[B,W,C], mask[B,W,C], depth[B,W])."""
    items = [dataset[i] for i in indices]
    return (torch.stack([x for x, _, _ in items]),
            torch.stack([m for _, m, _ in items]),
            torch.stack([d for _, _, d in items]))


def _depth_loss(pred: torch.Tensor, depth_mm: torch.Tensor,
                frame_ok: torch.Tensor) -> torch.Tensor:
    """MSE in symlog space at frames with real data.

    pred is already in symlog space (the head's output); the target is
    symlog(depth_mm). frame_ok [B, T] marks frames whose sensor values are
    present — goldak is fully observed so this is all frames, but graded the
    same mask-aware way the SSL arms are so the objective is the only change.
    """
    target = symlog(depth_mm)
    if not frame_ok.any():
        return torch.zeros((), device=pred.device)
    return F.mse_loss(pred[frame_ok], target[frame_ok])


@torch.no_grad()
def evaluate(model: SupervisedDepthModel, windows: DepthWindows,
             batch_size: int = 64, device: str = "cpu") -> dict:
    """Held-out depth error: symlog-space MSE plus MAE back in real mm.

    The mm MAE is reported so the number is directly comparable to Gate 1.5's
    supervised baseline (0.109 mm); the mean-predictor baseline (predict the
    corpus-mean depth everywhere) is the "did it learn anything" floor, mirror
    of the recon/latent mean baselines the SSL arms print.
    """
    model.eval()
    sq = abs_err = abs_err_mean = n = 0.0
    depth_sum = depth_n = 0.0
    # first pass mean over the set (for the mean-predictor baseline)
    for i in range(0, len(windows), batch_size):
        _, mask, depth = stack_depth_windows(windows, range(i, min(i + batch_size, len(windows))))
        frame_ok = mask.any(dim=-1)
        depth_sum += float(depth[frame_ok].sum()); depth_n += float(frame_ok.sum())
    mean_depth = depth_sum / max(depth_n, 1)
    for i in range(0, len(windows), batch_size):
        x, mask, depth = stack_depth_windows(windows, range(i, min(i + batch_size, len(windows))))
        x, mask, depth = x.to(device), mask.to(device), depth.to(device)
        frame_ok = mask.any(dim=-1)
        if not frame_ok.any():
            continue
        pred = model(x, mask)                 # symlog space
        pred_mm = symexp(pred)                # back to mm
        d = depth[frame_ok]
        sq += float(((pred[frame_ok] - symlog(depth)[frame_ok]) ** 2).sum())
        abs_err += float((pred_mm[frame_ok] - d).abs().sum())
        abs_err_mean += float((d - mean_depth).abs().sum())
        n += float(frame_ok.sum())
    return {
        "n_windows": len(windows),
        "depth_mse_symlog": sq / max(n, 1),
        "depth_mae_mm": abs_err / max(n, 1),
        "depth_mae_mm_mean_baseline": abs_err_mean / max(n, 1),
    }


def pretrain_supervised_depth(train: list[SessionTensor], val: list[SessionTensor],
                              epochs: int, window: int = DEFAULT_WINDOW,
                              stride: int = STRIDE, batch_size: int = 64,
                              lr: float = 1e-3, device: str = "cpu",
                              seed: int = SEED, eval_every: int = 5
                              ) -> tuple[SupervisedDepthModel, dict]:
    """Train the encoder + depth head on symlog-depth MSE. Structure mirrors
    masked_recon.pretrain_windows exactly (seed order, shuffle RNG, batching) —
    the objective is the single line that differs."""
    seed_everything(seed)
    model = SupervisedDepthModel().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    train_ds = DepthWindows(train, window=window, stride=stride)
    val_ds = DepthWindows(val, window=window, stride=stride)
    order = list(range(len(train_ds)))
    shuffle_rng = random.Random(seed)
    history = {"loss": []}
    for epoch in range(epochs):
        model.train()
        shuffle_rng.shuffle(order)
        ep_loss, n_batches = 0.0, 0
        for i in range(0, len(order), batch_size):
            x, mask, depth = stack_depth_windows(train_ds, order[i:i + batch_size])
            x, mask, depth = x.to(device), mask.to(device), depth.to(device)
            pred = model(x, mask)
            loss = _depth_loss(pred, depth, mask.any(dim=-1))
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            ep_loss += float(loss.detach()); n_batches += 1
        history["loss"].append(ep_loss / max(n_batches, 1))

        if (epoch + 1) % eval_every == 0 or epoch == epochs - 1:
            m = evaluate(model, val_ds, device=device)
            print(f"epoch {epoch + 1:3d}  loss {history['loss'][-1]:.5f}  "
                  f"val depth MAE {m['depth_mae_mm']:.4f} mm "
                  f"(mean-baseline {m['depth_mae_mm_mean_baseline']:.4f} mm)")
    return model, history


def main():
    from world_model.data.splits import split_sessions
    from world_model.eval.eval_world_model import append_run
    from world_model.pretraining.common import save_transfer_checkpoint

    p = argparse.ArgumentParser(
        description="Supervised-on-simulated-depth pre-training (C8 / T5 / D4)")
    p.add_argument("--tiny", action="store_true", help=f"dev preset: {TINY}")
    p.add_argument("--limit", type=int, default=None,
                   help="unused for goldak (kept for corpus-arg symmetry)")
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--device", default="cpu", choices=["cpu", "mps", "cuda"])
    p.add_argument("--seed", type=int, default=SEED)
    p.add_argument("--window", type=int, default=DEFAULT_WINDOW)
    p.add_argument("--stride", type=int, default=STRIDE)
    add_corpus_args(p)
    args = p.parse_args()
    if args.corpus != "goldak":
        p.error("supervised_depth needs per-frame fusion-depth labels, which "
                "only the goldak corpus supplies — pass --corpus goldak "
                "(--corpus-variant wide is the C8 run).")
    epochs = TINY["epochs"] if args.tiny else args.epochs

    sessions, corpus_config = load_corpus(args)
    splits = split_sessions(sessions, seed=args.seed)
    print({k: len(v) for k, v in splits.items()},
          f"corpus={args.corpus}/{args.corpus_variant} "
          f"window={args.window} stride={args.stride}")

    model, history = pretrain_supervised_depth(
        splits["train"], splits["val"], epochs=epochs, window=args.window,
        stride=args.stride, device=args.device, seed=args.seed)

    test_ds = DepthWindows(splits["test"], window=args.window, stride=args.stride)
    m = evaluate(model, test_ds, device=args.device)
    learned = m["depth_mae_mm"] < 0.5 * m["depth_mae_mm_mean_baseline"]
    print(f"TEST depth MAE {m['depth_mae_mm']:.4f} mm "
          f"(mean-baseline {m['depth_mae_mm_mean_baseline']:.4f} mm)  "
          f"symlog MSE {m['depth_mse_symlog']:.5f}  "
          f"{'learned' if learned else 'KILL — no better than mean predictor'}")

    config = dict(model="supervised_depth", epochs=epochs, hidden=HIDDEN_DIM,
                  window=args.window, stride=args.stride, seed=args.seed)
    config.update(corpus_config)   # goldak fingerprint/seed/size identify the run
    # depth is the fusion_mae_mm column's whole reason for existing; the SSL
    # probe F1 columns stay empty here. note must stay comma-free (runs.csv).
    config_hash = append_run(
        "supervised_depth", config, args.seed, split="test",
        metrics=dict(n=m["n_windows"], quality_f1_macro=None,
                     fusion_mae_mm=m["depth_mae_mm"], per_class_recall=None),
        note=(f"supervised depth; mae_mm={m['depth_mae_mm']:.4f} "
              f"mean_baseline={m['depth_mae_mm_mean_baseline']:.4f} "
              f"symlog_mse={m['depth_mse_symlog']:.5f} "
              f"gate={'pass' if learned else 'KILL'}"))

    ckpt = CHECKPOINTS_DIR / f"supervised_depth_{config_hash}.pt"
    save_transfer_checkpoint(ckpt, model, objective="supervised_depth",
                             config=config, extras={"test_metrics": m})
    print(f"transfer artifact: {ckpt}")


if __name__ == "__main__":
    main()
