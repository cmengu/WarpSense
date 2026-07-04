"""
train_gru.py trains the GRU baseline on split mock sessions with channel dropout, logs validation metrics to runs.csv, and saves a checkpoint (STEPS.md Step 3; mock data is plumbing only per D4).

CLI (from backend/):
  python -m world_model.training.train_gru --tiny
  python -m world_model.training.train_gru --n-sessions 500 --epochs 40 --device mps

For newcomers — the training lifecycle, step by step:
  1. Seed all random generators, so a rerun with the same seed reproduces the
     same result.
  2. Load sessions and split them 70/15/15 by session (data/splits.py).
  3. Fit the input normaliser on the train split only (no leakage).
  4. Compute class weights: defective welds are rare, so their loss is scaled
     up (inverse frequency) — otherwise the model wins by ignoring them.
  5. Loop over epochs (one epoch = one full pass over the train set). Per
     batch of 8 sessions: apply random channel dropout, forward pass, compute
     the LOSS (one number measuring how wrong the predictions are:
     cross-entropy for quality, MSE for depth when labels exist), then
     backpropagation — compute how to nudge every weight to shrink the loss —
     and let the Adam optimizer apply the nudges. Thousands of repetitions;
     the loss trends down; the model improves.
  6. Every few epochs, score on the VAL split and log to runs.csv — this is
     how you watch progress and spot overfitting (train loss falling while
     val score stalls).
  7. At the end, score once on the untouched TEST split and save the weights
     as a checkpoint.

  --tiny (200 sessions, 20 epochs) runs in ~2 min on a laptop CPU — a preset
  for checking the pipeline works, not for producing numbers. All the knobs
  here (Adam @ 1e-3, batch 8, dropout 0.15) are standard, unexotic defaults.
"""

import argparse
import random

import numpy as np
import torch
import torch.nn.functional as F

from world_model.config import EXPERIMENTS_DIR, QUALITY_CLASSES, SEED, TINY
from world_model.architecture.stems import random_channel_dropout
from world_model.baselines.gru_baseline import GRUBaseline
from world_model.data.batch import collate_sessions
from world_model.data.loader_mock import load_mock_corpus
from world_model.data.schema import SessionTensor
from world_model.data.splits import split_sessions
from world_model.eval.eval_world_model import append_run, evaluate

CHECKPOINTS_DIR = EXPERIMENTS_DIR / "checkpoints"


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def class_weights(sessions: list[SessionTensor]) -> torch.Tensor:
    """Inverse-frequency weights so DEFECTIVE isn't drowned by the GOOD majority."""
    counts = torch.ones(len(QUALITY_CLASSES))  # +1 smoothing; no zero-division
    for s in sessions:
        label = s.meta.get("quality_class")
        if label is not None:
            counts[QUALITY_CLASSES.index(label)] += 1
    weights = counts.sum() / counts
    return weights / weights.mean()


def train_gru(train: list[SessionTensor], val: list[SessionTensor],
              epochs: int, batch_size: int = 8, lr: float = 1e-3,
              channel_dropout_p: float = 0.15, device: str = "cpu",
              seed: int = SEED, eval_every: int = 5,
              log_note: str = "", runs_csv=None) -> tuple[GRUBaseline, dict]:
    from world_model.eval.eval_world_model import RUNS_CSV
    runs_csv = runs_csv or RUNS_CSV
    seed_everything(seed)
    model = GRUBaseline().to(device)
    model.fit_normalizer(train)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    weights = class_weights(train).to(device)
    config = dict(model="gru_baseline", epochs=epochs, batch_size=batch_size, lr=lr,
                  channel_dropout_p=channel_dropout_p, n_train=len(train), seed=seed)

    dropout_gen = torch.Generator(device="cpu").manual_seed(seed)
    order = list(range(len(train)))
    shuffle_rng = random.Random(seed)
    history = {"loss": []}
    for epoch in range(epochs):
        model.train()
        shuffle_rng.shuffle(order)
        epoch_loss, n_batches = 0.0, 0
        for i in range(0, len(order), batch_size):
            batch = collate_sessions([train[j] for j in order[i:i + batch_size]])
            # channel dropout on CPU mask before device transfer (generator lives on CPU)
            batch.mask = random_channel_dropout(batch.mask, channel_dropout_p, dropout_gen)
            batch = batch.to(device)
            out = model(batch.x, batch.mask)
            labelled = batch.quality >= 0
            loss = torch.zeros((), device=device)
            if labelled.any():
                loss = loss + F.cross_entropy(out["quality_logits"][labelled],
                                              batch.quality[labelled], weight=weights)
            if batch.has_depth.any():
                d_true = batch.depth[batch.has_depth][:, -1]  # end-of-weld depth
                loss = loss + F.mse_loss(out["depth_mm"][batch.has_depth], d_true)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            epoch_loss += float(loss.detach())
            n_batches += 1
        history["loss"].append(epoch_loss / max(n_batches, 1))

        if (epoch + 1) % eval_every == 0 or epoch == epochs - 1:
            metrics = evaluate(model, val, device=device)
            append_run("gru_baseline", config, seed, split="val", metrics=metrics,
                       note=f"epoch={epoch + 1} {log_note}".strip(), runs_csv=runs_csv)
            print(f"epoch {epoch + 1:3d}  loss {history['loss'][-1]:.4f}  "
                  f"val macro-F1 {metrics['quality_f1_macro']:.3f}")
    return model, history


def main():
    p = argparse.ArgumentParser(description="Train the GRU baseline (Gate 3 opponent)")
    p.add_argument("--tiny", action="store_true", help=f"dev preset: {TINY}")
    p.add_argument("--n-sessions", type=int, default=500)
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--num-frames", type=int, default=1500)
    p.add_argument("--device", default="cpu", choices=["cpu", "mps", "cuda"])
    p.add_argument("--seed", type=int, default=SEED)
    args = p.parse_args()
    n_sessions = TINY["n_sessions"] if args.tiny else args.n_sessions
    epochs = TINY["epochs"] if args.tiny else args.epochs

    print(f"loading {n_sessions} mock sessions (plumbing check only — D4)")
    corpus = load_mock_corpus(n_sessions, num_frames=args.num_frames)
    splits = split_sessions(corpus, seed=args.seed)
    print({k: len(v) for k, v in splits.items()})

    model, _ = train_gru(splits["train"], splits["val"], epochs=epochs,
                         device=args.device, seed=args.seed,
                         log_note="mock/plumbing" + (" tiny" if args.tiny else ""))

    metrics = evaluate(model, splits["test"], device=args.device)
    config_hash = append_run("gru_baseline", dict(final=True, seed=args.seed),
                             args.seed, split="test", metrics=metrics,
                             note="mock/plumbing final")
    print(f"TEST macro-F1 {metrics['quality_f1_macro']:.3f}  "
          f"per-class recall {metrics['per_class_recall']}")

    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
    ckpt = CHECKPOINTS_DIR / f"gru_mock_{config_hash}.pt"
    torch.save(model.state_dict(), ckpt)
    print(f"checkpoint: {ckpt}")


if __name__ == "__main__":
    main()
