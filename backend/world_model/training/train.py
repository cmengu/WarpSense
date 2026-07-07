"""
train.py is the Step 8 training loop: warm-start from the Step 6 Polito artifact, five scheduled losses, channel dropout, runs.csv rows per epoch-block, and the z_phys sanity plot (STEPS.md Step 8; mock data is plumbing only per D4).

CLI (from backend/):
  python -m world_model.training.train --tiny
  python -m world_model.training.train --n-sessions 200 --epochs 40 --device mps

For newcomers — what differs from train_gru.py (same lifecycle otherwise):
  1. Warm start (D5): the volts/amps stems and the encoder GRU cell are
     initialised from the newest polito_pretrain_*.pt transfer artifact —
     weights that have seen REAL electrical weld dynamics — instead of random.
     Random init if no artifact exists (a warning says so; the plan's default
     is warm).
  2. Five losses on the fade-in schedule (losses.py), not two. The schedule
     breakpoints are written for the 300-epoch Step 11 run; here they are
     scaled by epochs/300 so short runs keep the shape.
  3. The ODE makes each step ~50× a GRU step: dopri5 + adjoint per batch.
     Hence --num-frames trims mock sessions (default 300 ≈ 3 s of weld —
     enough for arc-on/arc-off structure) and the batch stays small.
  4. Every eval block appends a runs.csv row (D11) with the loss mix in the
     note; the final artifacts are a checkpoint (norm buffers inside, same
     discipline as the GRU) and a z_phys timeline plot for one val session —
     the Step 8 done-when is recon ↓ plus z_phys visibly tracking arc-on/off.

The 11 engineered features (L_aux targets + quality-head fusion input) are
computed ONCE per session up front via the existing extractor — reuse, don't
reimplement (D2). Sessions the extractor rejects (too few arc-on frames) get
feats_valid=False: their aux loss is skipped and the quality head sees zeros,
which the decoder already treats as "features absent".
"""

import argparse
import random
from pathlib import Path

import torch

from world_model.config import (
    CHANNELS,
    EXPERIMENTS_DIR,
    N_FEATURES,
    SEED,
    TINY,
)
from world_model.architecture.stems import random_channel_dropout
from world_model.architecture.world_model import WeldWorldModel
from world_model.data.batch import Batch, collate_sessions
from world_model.data.loader_mock import load_mock_corpus
from world_model.data.schema import SessionTensor
from world_model.data.splits import split_sessions
from world_model.eval.eval_world_model import append_run, evaluate
from world_model.training.losses import compute_losses, total_loss
from world_model.training.symlog import PercentileNorm, symexp
from world_model.training.train_gru import class_weights, seed_everything

CHECKPOINTS_DIR = EXPERIMENTS_DIR / "checkpoints"
FULL_RUN_EPOCHS = 300  # the Step 11 schedule the fade breakpoints assume
# Keep ≥ 250: mock stitch sessions cycle 220 frames arc-on / 30 arc-off, and
# below one full cycle the corpus contains NO arc-off transitions — the heat
# channel stays ~0 and z_phys has nothing to learn from. ODE cost is linear in T.
TINY_NUM_FRAMES = 300


def session_features_11(session: SessionTensor) -> torch.Tensor | None:
    """The 11 engineered features via the EXISTING extractor (D2: reuse).
    None when the extractor rejects the session (too few arc-on frames)."""
    from warpsense.features.session_feature_extractor import SessionFeatureExtractor

    frames = [
        {name: (float(session.x[t, c]) if session.mask[t, c] else None)
         for c, name in enumerate(CHANNELS)}
        for t in range(session.T)
    ]
    try:
        feats = SessionFeatureExtractor().extract(session.session_id, frames)
    except (ValueError, KeyError):
        return None
    vec = list(feats.to_vector().values())  # dataclass field order — stable
    assert len(vec) == N_FEATURES
    return torch.tensor(vec, dtype=torch.float32)


def build_feats_lookup(sessions: list[SessionTensor]) -> dict[str, torch.Tensor]:
    """session_id → feats_11; sessions the extractor rejects are absent."""
    lookup = {}
    for s in sessions:
        vec = session_features_11(s)
        if vec is not None:
            lookup[s.session_id] = vec
    return lookup


def _feats_batch(batch: Batch, lookup: dict[str, torch.Tensor],
                 device: str) -> tuple[torch.Tensor, torch.Tensor]:
    """(feats [B, 11], valid [B]) — zeros where absent (decoder-native)."""
    B = len(batch.session_ids)
    feats = torch.zeros(B, N_FEATURES)
    valid = torch.zeros(B, dtype=torch.bool)
    for b, sid in enumerate(batch.session_ids):
        if sid in lookup:
            feats[b] = lookup[sid]
            valid[b] = True
    return feats.to(device), valid.to(device)


def latest_polito_artifact() -> Path | None:
    ckpts = sorted(CHECKPOINTS_DIR.glob("polito_pretrain_*.pt"),
                   key=lambda p: p.stat().st_mtime)
    return ckpts[-1] if ckpts else None


def load_polito_transfer(model: WeldWorldModel,
                         transfer_sd: dict[str, torch.Tensor]) -> list[str]:
    """D5 warm start: Polito trunk → encoder GRUCell (name-mapped), and the
    volts/amps stems copied by NAME — exactly the channels Polito trained."""
    model.encoder.load_pretrained_trunk(transfer_sd)
    loaded = ["encoder.cell"]
    with torch.no_grad():
        for name in ("volts", "amps"):
            conv = model.stems.stems[name]
            conv.weight.copy_(transfer_sd[f"stems.stems.{name}.weight"])
            conv.bias.copy_(transfer_sd[f"stems.stems.{name}.bias"])
            loaded.append(f"stems.{name}")
    return loaded


class WorldModelEvalAdapter:
    """predict(Batch) shim so the shared harness (eval_world_model.evaluate)
    scores the world model on the SAME code path as the GRU baseline. Depth
    comes back through symexp — the head predicts in symlog space."""

    def __init__(self, model: WeldWorldModel, feats_lookup: dict[str, torch.Tensor]):
        self.model = model
        self.feats_lookup = feats_lookup

    @torch.no_grad()
    def predict(self, batch: Batch) -> dict[str, torch.Tensor]:
        self.model.eval()
        device = batch.x.device
        feats, _ = _feats_batch(batch, self.feats_lookup, device)
        out = self.model(batch.x, batch.mask, feats=feats)
        return {
            "quality_probs": out["quality_logits"].softmax(dim=-1),
            "depth_mm": symexp(out["depth_hat"][:, -1]),  # end-of-weld depth
        }


def train(train_sessions: list[SessionTensor], val_sessions: list[SessionTensor],
          epochs: int, batch_size: int = 8, lr: float = 1e-3,
          channel_dropout_p: float = 0.15, device: str = "cpu", seed: int = SEED,
          eval_every: int = 5, transfer_sd: dict[str, torch.Tensor] | None = None,
          log_note: str = "", runs_csv=None) -> tuple[WeldWorldModel, dict]:
    from world_model.eval.eval_world_model import RUNS_CSV
    runs_csv = runs_csv or RUNS_CSV
    seed_everything(seed)

    model = WeldWorldModel().to(device)
    model.fit_normalizer(train_sessions)
    if transfer_sd is not None:
        loaded = load_polito_transfer(model, transfer_sd)
        print(f"warm start (D5): {', '.join(loaded)}")
    else:
        print("WARNING: no Polito transfer artifact — random init "
              "(run world_model.training.pretrain_polito first)")

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    weights = class_weights(train_sessions).to(device)
    feats_lookup = build_feats_lookup(train_sessions + val_sessions)
    quality_norm = PercentileNorm()
    schedule_scale = epochs / FULL_RUN_EPOCHS
    config = dict(model="world_model", epochs=epochs, batch_size=batch_size, lr=lr,
                  channel_dropout_p=channel_dropout_p, n_train=len(train_sessions),
                  schedule_scale=schedule_scale, warm_start=transfer_sd is not None,
                  seed=seed)

    dropout_gen = torch.Generator(device="cpu").manual_seed(seed)
    order = list(range(len(train_sessions)))
    shuffle_rng = random.Random(seed)
    history: dict[str, list[float]] = {
        k: [] for k in ("loss", "recon", "physics", "quality", "aux", "kl")}
    for epoch in range(epochs):
        model.train()
        shuffle_rng.shuffle(order)
        ep = {k: 0.0 for k in history}
        n_batches = 0
        for i in range(0, len(order), batch_size):
            batch = collate_sessions([train_sessions[j] for j in order[i:i + batch_size]])
            target_mask = batch.mask.clone()  # recon targets: PRE-dropout truth
            batch.mask = random_channel_dropout(batch.mask, channel_dropout_p, dropout_gen)
            batch = batch.to(device)
            target_mask = target_mask.to(device)
            feats, feats_valid = _feats_batch(batch, feats_lookup, device)

            out = model(batch.x, batch.mask, feats=feats)
            L = compute_losses(model, out, batch, target_mask,
                               feats_target=feats, feats_valid=feats_valid,
                               class_weights=weights)
            loss = total_loss(L, epoch, quality_norm, schedule_scale)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            ep["loss"] += float(loss.detach())
            for k, v in L.detached().items():
                ep[k] += v
            n_batches += 1

        for k in history:
            history[k].append(ep[k] / max(n_batches, 1))

        if (epoch + 1) % eval_every == 0 or epoch == epochs - 1:
            adapter = WorldModelEvalAdapter(model, feats_lookup)
            metrics = evaluate(adapter, val_sessions, device=device)
            mix = " ".join(f"{k}={history[k][-1]:.4f}" for k in
                           ("recon", "physics", "quality", "aux", "kl"))
            append_run("world_model", config, seed, split="val", metrics=metrics,
                       note=f"epoch={epoch + 1} {mix} {log_note}".strip(),
                       runs_csv=runs_csv)
            f1 = metrics["quality_f1_macro"]
            print(f"epoch {epoch + 1:3d}  loss {history['loss'][-1]:.4f}  "
                  f"recon {history['recon'][-1]:.4f}  "
                  f"val macro-F1 {f1 if f1 is None else f'{f1:.3f}'}")
    return model, history


def plot_z_phys(model: WeldWorldModel, session: SessionTensor):
    """The Step 8 done-when visual: z_phys traces over the session's channels —
    they should rise with arc-on and decay at arc-off. Returns the PNG path."""
    from world_model.viz.timeline import plot_session

    out = model.infer(session)
    return plot_session(session, extra={
        "z_phys": out["z_traj"][:, :4].numpy(),
        "depth_hat": symexp(out["depth_mm"]).numpy(),
    })


def main():
    p = argparse.ArgumentParser(description="Step 8: train the world model (mock/plumbing)")
    p.add_argument("--tiny", action="store_true", help=f"dev preset: {TINY}")
    p.add_argument("--n-sessions", type=int, default=200)
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--num-frames", type=int, default=TINY_NUM_FRAMES,
                   help="frames per mock session (ODE cost is linear in T)")
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--device", default="cpu", choices=["cpu", "mps", "cuda"])
    p.add_argument("--seed", type=int, default=SEED)
    p.add_argument("--pretrained", type=str, default=None,
                   help="polito_pretrain_*.pt path (default: newest in checkpoints/)")
    args = p.parse_args()
    n_sessions = TINY["n_sessions"] if args.tiny else args.n_sessions
    epochs = TINY["epochs"] if args.tiny else args.epochs

    artifact = Path(args.pretrained) if args.pretrained else latest_polito_artifact()
    transfer_sd = None
    if artifact is not None and artifact.exists():
        transfer_sd = torch.load(artifact, weights_only=True)["transfer_state_dict"]
        print(f"Polito transfer artifact: {artifact.name}")

    print(f"loading {n_sessions} mock sessions × {args.num_frames} frames "
          f"(plumbing check only — D4)")
    corpus = load_mock_corpus(n_sessions, num_frames=args.num_frames)
    splits = split_sessions(corpus, seed=args.seed)
    print({k: len(v) for k, v in splits.items()})

    model, history = train(splits["train"], splits["val"], epochs=epochs,
                           batch_size=args.batch_size, device=args.device,
                           seed=args.seed, transfer_sd=transfer_sd,
                           log_note="mock/plumbing" + (" tiny" if args.tiny else ""))

    feats_lookup = build_feats_lookup(splits["test"])
    metrics = evaluate(WorldModelEvalAdapter(model, feats_lookup), splits["test"],
                       device=args.device)
    config_hash = append_run("world_model", dict(final=True, seed=args.seed,
                                                 epochs=epochs, n_sessions=n_sessions,
                                                 num_frames=args.num_frames),
                             args.seed, split="test", metrics=metrics,
                             note="mock/plumbing final")
    print(f"TEST macro-F1 {metrics['quality_f1_macro']:.3f}  "
          f"per-class recall {metrics['per_class_recall']}")

    # Done-when, half 1: recon must trend DOWN over the run
    r = history["recon"]
    print(f"recon first→last: {r[0]:.4f} → {r[-1]:.4f} "
          f"({'↓ ok' if r[-1] < r[0] else 'NOT decreasing — investigate'})")

    # Done-when, half 2: z_phys traces vs arc-on/off, one val session
    png = plot_z_phys(model.cpu(), splits["val"][0])
    print(f"z_phys plot: {png}")

    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
    ckpt = CHECKPOINTS_DIR / f"world_model_mock_{config_hash}.pt"
    torch.save({"state_dict": model.state_dict(),
                "config": dict(epochs=epochs, n_sessions=n_sessions,
                               num_frames=args.num_frames, seed=args.seed),
                "history": history}, ckpt)
    print(f"checkpoint: {ckpt}")


if __name__ == "__main__":
    main()
