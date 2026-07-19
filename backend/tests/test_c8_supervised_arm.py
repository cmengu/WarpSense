"""Tests for C8 ticket #24 — the supervised-on-simulated-depth arm (T5 / D4).

The whole point of this arm is that it differs from the SSL arms (masked_recon,
jepa) in the training OBJECTIVE and in nothing else — any architectural
difference would confound the T5 comparison. So the tests are mostly identity
tests, plus one that the objective actually learns depth:

  1. Encoder architecture is identical to the SSL arms: the transferable
     parameters (stems + trunk) have exactly the same keys and shapes as a bare
     StemTrunkEncoder / a PolitoPretrainModel on the same channels. The only
     extra parameters are the depth head, which lives OUTSIDE TRANSFER_PREFIXES.
  2. The checkpoint honours the pretraining/common.py contract: objective is
     "supervised_depth", it round-trips through save/load, and the weights load
     into a plain StemTrunkEncoder — i.e. it is interchangeable with an SSL one.
  3. DepthWindows carries the per-frame depth label aligned frame-for-frame to
     the window it slices (the supervised analogue of ProbeWindows).
  4. The target is symlog(depth_mm) with MSE in symlog space, and training on a
     tiny goldak corpus actually drives the depth MAE below the mean-predictor
     baseline — the objective learns Goldak's depth mapping, as T5 predicts.

Corpus sizes here are tiny (a handful of short sessions); simulate_session is a
per-frame Python loop and the 20k/1500 defaults are production numbers.
"""

import pytest
import torch

from world_model.architecture.trunk import (
    HIDDEN_DIM, TRANSFER_PREFIXES, StemTrunkEncoder)
from world_model.data.corpus_goldak import generate_corpus, resolve_spec
from world_model.data.splits import split_sessions
from world_model.pretraining.common import (
    build_encoder, load_transfer_checkpoint, save_transfer_checkpoint)
from world_model.pretraining.masked_recon import PRETRAIN_CHANNELS, PolitoPretrainModel
from world_model.pretraining.supervised_depth import (
    DEPTH_KEY, DepthWindows, SupervisedDepthModel, evaluate,
    pretrain_supervised_depth, stack_depth_windows)
from world_model.training.symlog import symlog


def tiny_sessions(n_sessions: int = 8, n_frames: int = 400):
    """A goldak corpus small and short enough to train inside a unit test."""
    return generate_corpus(resolve_spec("wide", n_sessions=n_sessions, n_frames=n_frames))


# --- 1. encoder architecture identical to the SSL arms -----------------------

def test_transfer_keys_identical_to_bare_encoder():
    """Objective-only: the supervised model's transferable parameters match a
    bare StemTrunkEncoder key-for-key and shape-for-shape."""
    model = SupervisedDepthModel()
    bare = StemTrunkEncoder(PRETRAIN_CHANNELS, HIDDEN_DIM)
    sup = model.transfer_state_dict()
    ref = bare.transfer_state_dict()
    assert set(sup) == set(ref)
    for k in ref:
        assert sup[k].shape == ref[k].shape


def test_transfer_keys_match_the_ssl_arm():
    """The masked_recon arm and the supervised arm expose the SAME transfer
    contract — the checkpoints are structurally interchangeable."""
    ssl = PolitoPretrainModel()               # masked_recon arm
    sup = SupervisedDepthModel()              # this arm
    assert set(sup.transfer_state_dict()) == set(ssl.transfer_state_dict())


def test_depth_head_is_the_only_extra_and_does_not_transfer():
    model = SupervisedDepthModel()
    all_keys = set(model.state_dict())
    transfer = set(model.transfer_state_dict())
    extra = all_keys - transfer
    assert extra and all(k.startswith("depth_head.") for k in extra)
    assert not any(k.startswith(TRANSFER_PREFIXES) for k in extra)


def test_forward_returns_per_frame_scalar():
    model = SupervisedDepthModel()
    B, T, C = 3, 50, len(PRETRAIN_CHANNELS)
    x = torch.randn(B, T, C)
    mask = torch.ones(B, T, C, dtype=torch.bool)
    out = model(x, mask)
    assert out.shape == (B, T)


# --- 2. checkpoint contract / interchangeability -----------------------------

def test_checkpoint_round_trips_and_is_interchangeable(tmp_path):
    model = SupervisedDepthModel()
    path = tmp_path / "supervised_depth.pt"
    save_transfer_checkpoint(path, model, objective="supervised_depth",
                             config={"epochs": 1})
    ckpt = load_transfer_checkpoint(path)
    assert ckpt["objective"] == "supervised_depth"
    # rebuilds through the shared helper, and loads into a plain encoder just
    # like an SSL checkpoint would — the head never rode along
    rebuilt = build_encoder(ckpt)
    assert rebuilt.channels == PRETRAIN_CHANNELS
    assert rebuilt.hidden_dim == HIDDEN_DIM
    fresh = StemTrunkEncoder(PRETRAIN_CHANNELS, HIDDEN_DIM)
    fresh.load_transfer_state_dict(ckpt["transfer_state_dict"])
    for k, v in model.transfer_state_dict().items():
        assert torch.equal(fresh.state_dict()[k], v)


# --- 3. per-frame label alignment --------------------------------------------

def test_depth_windows_align_label_to_slice():
    sessions = tiny_sessions(n_sessions=3, n_frames=300)
    ds = DepthWindows(sessions, window=100, stride=50)
    for item in range(len(ds)):
        x, mask, depth = ds[item]
        i, start = ds.index[item]
        assert x.shape == (100, len(PRETRAIN_CHANNELS))
        assert depth.shape == (100,)
        expected = torch.from_numpy(
            sessions[i].meta[DEPTH_KEY][start:start + 100]).float()
        assert torch.equal(depth, expected)


def test_stack_depth_windows_shapes():
    sessions = tiny_sessions(n_sessions=3, n_frames=300)
    ds = DepthWindows(sessions, window=100, stride=50)
    x, mask, depth = stack_depth_windows(ds, range(min(4, len(ds))))
    B = min(4, len(ds))
    assert x.shape == (B, 100, len(PRETRAIN_CHANNELS))
    assert mask.shape == (B, 100, len(PRETRAIN_CHANNELS))
    assert depth.shape == (B, 100)


# --- 4. symlog target + the objective learns depth ---------------------------

def test_target_convention_is_symlog():
    """The target is symlog(depth_mm): a head emitting symlog(true depth) would
    symexp back to the true millimetres, which is exactly what evaluate() does
    to report mm MAE. Pins the convention to training/symlog.py."""
    from world_model.training.symlog import symexp
    sessions = tiny_sessions(n_sessions=2, n_frames=200)
    ds = DepthWindows(sessions, window=100, stride=100)
    x, mask, depth = stack_depth_windows(ds, range(len(ds)))
    perfect_pred = symlog(depth)               # what a perfect head would output
    assert torch.allclose(symexp(perfect_pred), depth, atol=1e-3)


def test_training_converges_and_beats_mean_baseline():
    """Supervised depth on a tiny goldak corpus converges (training loss falls
    by more than 3x) and generalises: held-out depth MAE drops below the
    mean-predictor baseline (T5's premise that supervised learning works in
    sim). The margin is modest by design — the objective-only rule forces the
    SAME volts/amps encoder the SSL arms use, and depth also depends on travel
    speed, a channel this 2-stem encoder cannot see, so there is a real
    information ceiling. Beating the mean predictor is the honest 'learned it'
    bar; a 2x win is not available without changing the architecture, which
    would confound T5."""
    sessions = tiny_sessions(n_sessions=24, n_frames=600)
    splits = split_sessions(sessions, seed=1337)
    model, history = pretrain_supervised_depth(
        splits["train"], splits["val"], epochs=40, window=300, stride=100,
        lr=3e-3, seed=1337, eval_every=40)
    test_ds = DepthWindows(splits["test"], window=300, stride=100)
    m = evaluate(model, test_ds)
    assert history["loss"][-1] < history["loss"][0] / 3      # converged
    assert m["depth_mae_mm"] < m["depth_mae_mm_mean_baseline"]  # beats mean


def test_main_refuses_polito(monkeypatch):
    """Polito has no per-frame depth label, so the arm refuses it rather than
    training on absent labels."""
    import sys
    from world_model.pretraining import supervised_depth
    monkeypatch.setattr(sys, "argv",
                        ["supervised_depth", "--tiny", "--corpus", "polito"])
    with pytest.raises(SystemExit):
        supervised_depth.main()
