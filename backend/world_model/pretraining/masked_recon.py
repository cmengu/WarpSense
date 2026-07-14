"""
masked_recon.py (formerly training/pretrain_polito.py) pre-trains the volts/amps
stems + GRU trunk on the 1,976 real Polito spot welds via masked-timestep
reconstruction + fault-bit prediction, and saves the transfer artifact that
warm-starts the world model (STEPS.md Step 6, D5).

CLI (from backend/; the old training.pretrain_polito path still works via shim):
  python -m world_model.pretraining.masked_recon --tiny
  python -m world_model.pretraining.masked_recon --epochs 30 --device mps
  python -m world_model.pretraining.masked_recon --window 300  # C4-C7 control diet

This is Gate 0.5. Two purposes:
  1. Warm start: the ONLY real data in the repo today is Polito (spot welding,
     volts/amps only). It cannot train the final model — wrong process, 2 of 6
     channels, no quality taxonomy — but it can teach the stems and trunk what
     REAL electrical weld dynamics look like, so Step 8 starts from those
     weights instead of random. Modest expectations, pre-registered (D5).
  2. Kill criterion, checked early: if this pipeline cannot learn real
     electrical dynamics at all (recon no better than predicting the mean),
     the architecture has a problem — find out now, not after Steps 7–8.

Objectives (both, jointly):
  - Masked reconstruction (the BERT recipe on time series): hide 15% of
    timesteps from the encoder input, reconstruct the sensor values at the
    hidden frames from the trunk's hidden state. No labels needed; forces the
    trunk to model temporal structure. The trunk is causal (GRU), so it
    reconstructs a masked frame from the past — harder than bidirectional
    infilling, which is fine for a representation objective.
  - Fault bit: one logit per weld from the last hidden state. 79 faulty vs
    1,897 good → BCE with pos_weight = n_good/n_faulty, else the model wins
    by always answering "good".

What transfers and what doesn't:
  - TRANSFERS: stems["volts"], stems["amps"] (ChannelStems keyed by channel
    NAME — precisely these two exist here), and the trunk. The trunk is a
    single-layer nn.GRU; its weight_ih_l0/weight_hh_l0/bias_* are
    shape-identical to nn.GRUCell's weight_ih/weight_hh/bias_* — Step 8 maps
    the names when initialising the ODE-RNN encoder cell.
  - DOES NOT transfer: recon head, fault head (pretrain-only scaffolding).
  - Force: present in the CSVs but has no slot in the 6-channel contract; the
    spec marks a force stem optional. Omitted — a third stem would not
    transfer, and the two channels that do are the point.

No input normalisation here: Polito values arrive pre-normalised to [0,1] by
the dataset authors (loader_polito.py). Re-standardising them with statistics
the ESP32 path will never reproduce would poison the transfer.
"""

import argparse
import random

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from world_model.config import CHANNEL_INDEX, EXPERIMENTS_DIR, SEED, TINY
from world_model.architecture.trunk import HIDDEN_DIM, StemTrunkEncoder
from world_model.data.batch import collate_sessions
from world_model.data.loader_polito import load_polito_sessions
from world_model.data.schema import SessionTensor
from world_model.data.splits import split_sessions
from world_model.data.windows import TrainWindows, stack_windows
from world_model.data.windows import mask_timesteps as _mask_timesteps

CHECKPOINTS_DIR = EXPERIMENTS_DIR / "checkpoints"
RUNS_CSV = EXPERIMENTS_DIR / "runs.csv"

PRETRAIN_CHANNELS = ["volts", "amps"]
MASK_FRACTION = 0.15


class PolitoPretrainModel(StemTrunkEncoder):
    """The shared stems+trunk encoder plus two masked-recon-only heads.

    Subclasses StemTrunkEncoder (rather than wrapping it) so parameter names
    and RNG creation order are identical to the pre-refactor class: existing
    checkpoints load bit-for-bit and seeded runs reproduce exactly.
    """

    def __init__(self, hidden_dim: int = HIDDEN_DIM):
        super().__init__(PRETRAIN_CHANNELS, hidden_dim)
        self.recon_head = nn.Linear(hidden_dim, len(PRETRAIN_CHANNELS))
        self.fault_head = nn.Linear(hidden_dim, 1)

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> dict[str, torch.Tensor]:
        """x, mask: [B, T, 2] (volts, amps only). Returns recon + fault logit."""
        out = self.encode(x, mask)       # [B, T, HIDDEN]
        return {
            "recon": self.recon_head(out),            # [B, T, 2]
            "fault_logit": self.fault_head(out[:, -1]).squeeze(-1),  # [B]
        }


def _two_channel_batch(sessions: list[SessionTensor]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Collate and slice to (x[B,T,2], mask[B,T,2], fault[B]) — volts, amps."""
    batch = collate_sessions(sessions)
    cols = [CHANNEL_INDEX[c] for c in PRETRAIN_CHANNELS]
    fault = torch.tensor([float(s.meta["fault"]) for s in sessions])
    return batch.x[:, :, cols], batch.mask[:, :, cols], fault


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


@torch.no_grad()
def evaluate(model: PolitoPretrainModel, sessions: list[SessionTensor],
             batch_size: int = 32, seed: int = SEED,
             device: str = "cpu") -> dict:
    """Held-out masked-recon MSE (vs mean-predictor baseline) + fault macro-F1."""
    model.eval()
    gen = torch.Generator().manual_seed(seed + 1)  # fixed eval mask, ≠ train stream
    sq_err = sq_err_mean = n_recon = 0.0
    tp = fp = fn = tn = 0
    for i in range(0, len(sessions), batch_size):
        x, mask, fault = _two_channel_batch(sessions[i:i + batch_size])
        input_mask, hidden = _mask_timesteps(mask, MASK_FRACTION, gen)
        x, mask, fault = x.to(device), mask.to(device), fault.to(device)
        out = model(x * input_mask.to(device), input_mask.to(device))
        target = hidden.unsqueeze(-1).to(device) & mask  # hidden frames, real values only
        if target.any():
            err = (out["recon"] - x)[target]
            sq_err += float((err ** 2).sum())
            # baseline: predict each channel's batch mean at every hidden frame
            ch_mean = (x * mask).sum(dim=(0, 1)) / mask.sum(dim=(0, 1)).clamp(min=1)
            sq_err_mean += float(((x - ch_mean)[target] ** 2).sum())
            n_recon += float(target.sum())
        pred = out["fault_logit"] > 0
        truth = fault > 0.5
        tp += int((pred & truth).sum()); fp += int((pred & ~truth).sum())
        fn += int((~pred & truth).sum()); tn += int((~pred & ~truth).sum())

    def f1(tp_, fp_, fn_):
        return 2 * tp_ / max(2 * tp_ + fp_ + fn_, 1)

    return {
        "n": len(sessions),
        "recon_mse": sq_err / max(n_recon, 1),
        "recon_mse_mean_baseline": sq_err_mean / max(n_recon, 1),
        "fault_f1_macro": (f1(tp, fp, fn) + f1(tn, fn, fp)) / 2,
        "fault_confusion": dict(tp=tp, fp=fp, fn=fn, tn=tn),
    }


def pretrain(train: list[SessionTensor], val: list[SessionTensor],
             epochs: int, batch_size: int = 32, lr: float = 1e-3,
             fault_loss_weight: float = 0.2, device: str = "cpu",
             seed: int = SEED, eval_every: int = 5) -> tuple[PolitoPretrainModel, dict]:
    seed_everything(seed)
    model = PolitoPretrainModel().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    n_fault = sum(int(s.meta["fault"]) for s in train)
    pos_weight = torch.tensor((len(train) - n_fault) / max(n_fault, 1), device=device)

    mask_gen = torch.Generator().manual_seed(seed)
    order = list(range(len(train)))
    shuffle_rng = random.Random(seed)
    history = {"loss": [], "recon": [], "fault": []}
    for epoch in range(epochs):
        model.train()
        shuffle_rng.shuffle(order)
        ep = dict(loss=0.0, recon=0.0, fault=0.0, n=0)
        for i in range(0, len(order), batch_size):
            x, mask, fault = _two_channel_batch([train[j] for j in order[i:i + batch_size]])
            input_mask, hidden = _mask_timesteps(mask, MASK_FRACTION, mask_gen)
            x, mask, fault = x.to(device), mask.to(device), fault.to(device)
            input_mask = input_mask.to(device)

            out = model(x * input_mask, input_mask)
            target = hidden.unsqueeze(-1).to(device) & mask
            recon_loss = (F.mse_loss(out["recon"], x, reduction="none")[target].mean()
                          if target.any() else torch.zeros((), device=device))
            fault_loss = F.binary_cross_entropy_with_logits(
                out["fault_logit"], fault, pos_weight=pos_weight)
            loss = recon_loss + fault_loss_weight * fault_loss

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            ep["loss"] += float(loss.detach()); ep["recon"] += float(recon_loss.detach())
            ep["fault"] += float(fault_loss.detach()); ep["n"] += 1

        n = max(ep["n"], 1)
        history["loss"].append(ep["loss"] / n)
        history["recon"].append(ep["recon"] / n)
        history["fault"].append(ep["fault"] / n)

        if (epoch + 1) % eval_every == 0 or epoch == epochs - 1:
            m = evaluate(model, val, seed=seed, device=device)
            print(f"epoch {epoch + 1:3d}  loss {history['loss'][-1]:.4f}  "
                  f"val recon MSE {m['recon_mse']:.5f} "
                  f"(mean-baseline {m['recon_mse_mean_baseline']:.5f})  "
                  f"fault macro-F1 {m['fault_f1_macro']:.3f}")
    return model, history


# ------------------------------------------------ window diet (C4-C7 spec)
# The C7 head-to-head must change exactly one variable — the objective — so
# masked recon gets re-trained on the SAME TrainWindows diet JEPA trains on
# (window=300, stride=50). TrainWindows carries no labels by type, so this
# path is recon-only: the fault head stays untrained scaffolding. The Step-6
# whole-session run above remains the historical reference.

@torch.no_grad()
def evaluate_windows(model: PolitoPretrainModel, windows: TrainWindows,
                     batch_size: int = 64, seed: int = SEED,
                     device: str = "cpu") -> dict:
    """Held-out masked-recon MSE on windows (vs mean-predictor baseline)."""
    model.eval()
    gen = torch.Generator().manual_seed(seed + 1)  # fixed eval mask, ≠ train stream
    sq_err = sq_err_mean = n_recon = 0.0
    for i in range(0, len(windows), batch_size):
        x, mask = stack_windows(windows, range(i, min(i + batch_size, len(windows))))
        input_mask, hidden = _mask_timesteps(mask, MASK_FRACTION, gen)
        x, mask = x.to(device), mask.to(device)
        out = model(x * input_mask.to(device), input_mask.to(device))
        target = hidden.unsqueeze(-1).to(device) & mask
        if target.any():
            err = (out["recon"] - x)[target]
            sq_err += float((err ** 2).sum())
            ch_mean = (x * mask).sum(dim=(0, 1)) / mask.sum(dim=(0, 1)).clamp(min=1)
            sq_err_mean += float(((x - ch_mean)[target] ** 2).sum())
            n_recon += float(target.sum())
    return {
        "n_windows": len(windows),
        "recon_mse": sq_err / max(n_recon, 1),
        "recon_mse_mean_baseline": sq_err_mean / max(n_recon, 1),
    }


def pretrain_windows(train: list[SessionTensor], val: list[SessionTensor],
                     epochs: int, window: int = 300, stride: int = 50,
                     batch_size: int = 64, lr: float = 1e-3, device: str = "cpu",
                     seed: int = SEED, eval_every: int = 5
                     ) -> tuple[PolitoPretrainModel, dict]:
    seed_everything(seed)
    model = PolitoPretrainModel().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

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
            input_mask, hidden = _mask_timesteps(mask, MASK_FRACTION, mask_gen)
            x, mask = x.to(device), mask.to(device)
            input_mask = input_mask.to(device)
            out = model(x * input_mask, input_mask)
            target = hidden.unsqueeze(-1).to(device) & mask
            loss = (F.mse_loss(out["recon"], x, reduction="none")[target].mean()
                    if target.any() else torch.zeros((), device=device))
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            ep_loss += float(loss.detach()); n_batches += 1
        history["loss"].append(ep_loss / max(n_batches, 1))

        if (epoch + 1) % eval_every == 0 or epoch == epochs - 1:
            m = evaluate_windows(model, val_ds, seed=seed, device=device)
            print(f"epoch {epoch + 1:3d}  loss {history['loss'][-1]:.5f}  "
                  f"val recon MSE {m['recon_mse']:.5f} "
                  f"(mean-baseline {m['recon_mse_mean_baseline']:.5f})")
    return model, history


def main():
    from world_model.eval.eval_world_model import append_run

    p = argparse.ArgumentParser(description="Gate 0.5: Polito pre-training (Step 6)")
    p.add_argument("--tiny", action="store_true", help=f"dev preset: {TINY}")
    p.add_argument("--limit", type=int, default=None, help="read only first N welds")
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--device", default="cpu", choices=["cpu", "mps", "cuda"])
    p.add_argument("--seed", type=int, default=SEED)
    p.add_argument("--window", type=int, default=None,
                   help="train on TrainWindows of this length (the C4-C7 "
                        "one-variable diet) instead of whole sessions")
    p.add_argument("--stride", type=int, default=50)
    args = p.parse_args()
    limit = TINY["n_sessions"] if args.tiny else args.limit
    epochs = TINY["epochs"] if args.tiny else args.epochs

    print(f"loading Polito welds (limit={limit}) — the only REAL data in the repo")
    sessions = load_polito_sessions(limit=limit)
    splits = split_sessions(sessions, seed=args.seed)
    n_fault = sum(int(s.meta["fault"]) for s in sessions)
    print({k: len(v) for k, v in splits.items()}, f"faults={n_fault}/{len(sessions)}")

    if args.window:
        from world_model.pretraining.common import save_transfer_checkpoint

        model, history = pretrain_windows(
            splits["train"], splits["val"], epochs=epochs, window=args.window,
            stride=args.stride, device=args.device, seed=args.seed)
        test_ds = TrainWindows(splits["test"], window=args.window,
                               stride=args.stride, channels=PRETRAIN_CHANNELS)
        m = evaluate_windows(model, test_ds, seed=args.seed, device=args.device)
        learned = m["recon_mse"] < 0.5 * m["recon_mse_mean_baseline"]
        print(f"TEST recon MSE {m['recon_mse']:.5f} "
              f"(mean-baseline {m['recon_mse_mean_baseline']:.5f})  "
              f"{'learned' if learned else 'KILL — no better than mean predictor'}")

        config = dict(model="masked_recon_windows", epochs=epochs, limit=limit,
                      hidden=HIDDEN_DIM, mask_fraction=MASK_FRACTION,
                      window=args.window, stride=args.stride, seed=args.seed)
        # probe macro-F1 is C5's job; note stays comma-free (runs.csv)
        config_hash = append_run(
            "masked_recon_windows", config, args.seed, split="test",
            metrics=dict(n=m["n_windows"], quality_f1_macro=None,
                         fusion_mae_mm=None, per_class_recall=None),
            note=(f"window diet; recon_mse={m['recon_mse']:.5f} "
                  f"mean_baseline={m['recon_mse_mean_baseline']:.5f} "
                  f"gate={'pass' if learned else 'KILL'}"))
        ckpt = CHECKPOINTS_DIR / f"masked_recon_windows_{config_hash}.pt"
        save_transfer_checkpoint(ckpt, model, objective="masked_recon",
                                 config=config, extras={"test_metrics": m})
        print(f"transfer artifact: {ckpt}")
        return

    model, history = pretrain(splits["train"], splits["val"], epochs=epochs,
                              device=args.device, seed=args.seed)

    m = evaluate(model, splits["test"], seed=args.seed, device=args.device)
    print(f"TEST recon MSE {m['recon_mse']:.5f} "
          f"(mean-baseline {m['recon_mse_mean_baseline']:.5f})  "
          f"fault macro-F1 {m['fault_f1_macro']:.3f}  {m['fault_confusion']}")

    # Kill criterion (Gate 0.5): recon must beat the mean predictor decisively.
    learned = m["recon_mse"] < 0.5 * m["recon_mse_mean_baseline"]
    print("Gate 0.5:", "learned real electrical dynamics"
          if learned else "KILL — recon no better than mean predictor")

    config = dict(model="polito_pretrain", epochs=epochs, limit=limit,
                  hidden=HIDDEN_DIM, mask_fraction=MASK_FRACTION, seed=args.seed)
    # runs.csv schema is quality-centric; fault macro-F1 goes in its F1 column
    # with the note marking the task, recon numbers ride in the note (D11).
    config_hash = append_run(
        "polito_pretrain", config, args.seed, split="test",
        metrics=dict(n=m["n"], quality_f1_macro=m["fault_f1_macro"],
                     fusion_mae_mm=None, per_class_recall=m["fault_confusion"]),
        note=(f"polito fault-bit; recon_mse={m['recon_mse']:.5f} "
              f"mean_baseline={m['recon_mse_mean_baseline']:.5f} "
              f"gate0.5={'pass' if learned else 'KILL'}"))

    from world_model.pretraining.common import save_transfer_checkpoint

    ckpt = CHECKPOINTS_DIR / f"polito_pretrain_{config_hash}.pt"
    save_transfer_checkpoint(
        ckpt, model, objective="masked_recon", config=config,
        extras={"test_metrics": {k: v for k, v in m.items() if k != "fault_confusion"}})
    print(f"transfer artifact: {ckpt}")


if __name__ == "__main__":
    main()
