"""
Consolidation contract tests — shared encoder (architecture/trunk.py) and
windowing/masking (data/windows.py).

Pins the three guarantees the C1 refactor must keep forever:
  1. the transfer contract survives — the REAL Step 6 checkpoint still loads,
     and transfer keys keep their historical names;
  2. TrainWindows is label-free BY TYPE — self-supervised training cannot see
     labels because the sample physically doesn't carry them;
  3. the masking recipes hide whole frames and only frames they claim to hide.
"""

import numpy as np
import pytest
import torch

from world_model.architecture.trunk import HIDDEN_DIM, StemTrunkEncoder
from world_model.config import CHANNELS, EXPERIMENTS_DIR
from world_model.data.schema import SessionTensor
from world_model.data.windows import (
    ProbeWindows,
    TrainWindows,
    mask_contiguous,
    mask_timesteps,
)

STEP6_CKPT = EXPERIMENTS_DIR / "checkpoints" / "polito_pretrain_8a68998bf644.pt"


def _sessions(n=3, T=400, seed=0):
    rng = np.random.default_rng(seed)
    return [
        SessionTensor(
            x=rng.random((T, len(CHANNELS))).astype(np.float32),
            mask=np.ones((T, len(CHANNELS)), dtype=bool),
            meta={"session_id": f"s{i}", "source": "mock",
                  "quality_class": "GOOD", "skill": "expert"},
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------- trunk

def test_real_step6_checkpoint_loads_into_shared_encoder():
    """The historical transfer artifact must warm-start the extracted encoder."""
    if not STEP6_CKPT.exists():
        pytest.skip("Step 6 checkpoint not present")
    ckpt = torch.load(STEP6_CKPT, weights_only=True)
    enc = StemTrunkEncoder(ckpt["channels"], ckpt["hidden_dim"])
    enc.load_transfer_state_dict(ckpt["transfer_state_dict"])
    loaded = enc.state_dict()["trunk.weight_ih_l0"]
    assert torch.equal(loaded, ckpt["transfer_state_dict"]["trunk.weight_ih_l0"])


def test_transfer_keys_keep_historical_names():
    enc = StemTrunkEncoder(["volts", "amps"])
    keys = set(enc.transfer_state_dict())
    assert keys, "transfer artifact is empty"
    for k in keys:
        assert k.startswith(("stems.stems.volts.", "stems.stems.amps.", "trunk.")), k


def test_load_transfer_rejects_incomplete_artifact():
    enc = StemTrunkEncoder(["volts", "amps"])
    partial = {k: v for k, v in enc.transfer_state_dict().items()
               if not k.startswith("trunk.")}
    with pytest.raises(KeyError):
        enc.load_transfer_state_dict(partial)


def test_encoder_output_shape():
    enc = StemTrunkEncoder(["volts", "amps"])
    out = enc(torch.rand(2, 50, 2), torch.ones(2, 50, 2, dtype=torch.bool))
    assert out.shape == (2, 50, HIDDEN_DIM)


# ---------------------------------------------------------------- windows

def test_train_windows_carry_no_labels():
    """The self-supervised sample is (x, mask) and NOTHING else — the guard
    that keeps labels out of pretraining by construction."""
    ds = TrainWindows(_sessions(), window=100, stride=50)
    sample = ds[0]
    assert isinstance(sample, tuple) and len(sample) == 2
    x, mask = sample
    assert x.shape == (100, len(CHANNELS)) and x.dtype == torch.float32
    assert mask.shape == x.shape and mask.dtype == torch.bool


def test_train_windows_count_and_channel_subset():
    # T=400, window=100, stride=50 → 7 windows per session
    ds = TrainWindows(_sessions(n=2), window=100, stride=50, channels=["volts", "amps"])
    assert len(ds) == 14
    x, mask = ds[0]
    assert x.shape == (100, 2)


def test_train_windows_skip_short_sessions():
    short = _sessions(n=1, T=50)
    assert len(TrainWindows(short, window=100)) == 0


def test_probe_windows_carry_labels_and_groups():
    ds = ProbeWindows(_sessions(n=2), label_keys=["quality_class", "absent"],
                      window=100, stride=50)
    x, mask, labels, group = ds[7]      # first window of session 1
    assert labels == {"quality_class": "GOOD", "absent": None}
    assert group == 1


# ---------------------------------------------------------------- masking

def test_mask_contiguous_hides_one_block():
    mask = torch.ones(8, 200, 2, dtype=torch.bool)
    gen = torch.Generator().manual_seed(0)
    input_mask, hidden = mask_contiguous(mask, (0.25, 0.5), gen)
    for b in range(8):
        idx = hidden[b].nonzero().squeeze(-1)
        assert 50 <= len(idx) <= 100                      # 25–50% of 200
        assert int(idx[-1] - idx[0]) == len(idx) - 1      # contiguous
    assert not input_mask[hidden].any()                   # hidden frames dark
    assert input_mask[~hidden].all()                      # visible untouched


def test_mask_timesteps_matches_step6_semantics():
    mask = torch.ones(4, 200, 2, dtype=torch.bool)
    gen = torch.Generator().manual_seed(0)
    input_mask, hidden = mask_timesteps(mask, 0.15, gen)
    assert 0.05 < hidden.float().mean() < 0.30
    assert not input_mask[hidden].any()
    assert input_mask[~hidden].all()


# ------------------------------------------------- checkpoint contract (C2)

def test_checkpoint_contract_round_trip(tmp_path):
    """save → load → rebuild encoder → weights identical, and the Step 7
    ODE-RNN encoder accepts the artifact — the full consumer chain."""
    from world_model.architecture.encoder import ODERNNEncoder
    from world_model.pretraining.common import (
        build_encoder, load_transfer_checkpoint, save_transfer_checkpoint)

    torch.manual_seed(3)
    enc = StemTrunkEncoder(["volts", "amps"])
    path = tmp_path / "jepa_test.pt"
    save_transfer_checkpoint(path, enc, objective="jepa",
                             config={"epochs": 1}, extras={"note": "test"})

    ckpt = load_transfer_checkpoint(path)
    assert ckpt["objective"] == "jepa" and ckpt["note"] == "test"
    rebuilt = build_encoder(ckpt)
    for k, v in enc.transfer_state_dict().items():
        assert torch.equal(rebuilt.state_dict()[k], v), k
    ODERNNEncoder().load_pretrained_trunk(ckpt["transfer_state_dict"])


def test_load_infers_masked_recon_for_precontract_step6_artifact():
    if not STEP6_CKPT.exists():
        pytest.skip("Step 6 checkpoint not present")
    from world_model.pretraining.common import build_encoder, load_transfer_checkpoint
    ckpt = load_transfer_checkpoint(STEP6_CKPT)
    assert ckpt["objective"] == "masked_recon"
    assert build_encoder(ckpt).hidden_dim == ckpt["hidden_dim"]


def test_contract_rejects_unknown_objective_and_shadowing_extras(tmp_path):
    from world_model.pretraining.common import save_transfer_checkpoint
    enc = StemTrunkEncoder(["volts", "amps"])
    with pytest.raises(ValueError, match="unknown objective"):
        save_transfer_checkpoint(tmp_path / "x.pt", enc, "dreamer", config={})
    with pytest.raises(ValueError, match="shadow"):
        save_transfer_checkpoint(tmp_path / "x.pt", enc, "jepa", config={},
                                 extras={"config": {}})


# ------------------------------------------------------- JEPA components (C3)

def _jepa_step(model, seed=0):
    """One representative JEPA loss computation on random data."""
    from world_model.data.windows import mask_contiguous
    torch.manual_seed(seed)
    x = torch.rand(4, 60, 2)
    mask = torch.ones(4, 60, 2, dtype=torch.bool)
    input_mask, hidden = mask_contiguous(mask, (0.25, 0.5),
                                         torch.Generator().manual_seed(seed))
    pred = model(x * input_mask, input_mask)
    tgt = model.target_encode(x, mask)
    return ((pred - tgt) ** 2)[hidden].mean()


def test_jepa_target_never_receives_gradients():
    """Collapse guard #1: loss.backward() must train online + predictor only."""
    from world_model.pretraining.jepa import JEPAPretrainModel
    model = JEPAPretrainModel(["volts", "amps"])
    _jepa_step(model).backward()
    assert all(p.grad is None for p in model.target.parameters())
    assert all(p.grad is not None for p in model.stems.parameters())
    assert all(p.grad is not None for p in model.trunk.parameters())
    assert all(p.grad is not None for p in model.predictor.parameters())


def test_jepa_ema_update_moves_target_at_decay_rate():
    """Collapse guard #2: target starts = online, then trails it by EMA."""
    from world_model.pretraining.jepa import JEPAPretrainModel
    model = JEPAPretrainModel(["volts", "amps"], ema_decay=0.9)
    online = model.trunk.weight_ih_l0
    target = model.target.trunk.weight_ih_l0
    assert torch.equal(target, online)          # exact copy at init
    before = target.clone()
    with torch.no_grad():
        online.add_(1.0)                        # student moves...
    model.ema_update()
    expected = 0.9 * before + 0.1 * online      # ...target follows at 1-decay
    assert torch.allclose(target, expected)


def test_jepa_transfer_checkpoint_is_online_encoder_only(tmp_path):
    """The saved artifact must carry stems+trunk of the ONLINE encoder and
    nothing of the predictor/target — contract-identical to masked_recon."""
    from world_model.pretraining.common import (
        build_encoder, load_transfer_checkpoint, save_transfer_checkpoint)
    from world_model.pretraining.jepa import JEPAPretrainModel

    model = JEPAPretrainModel(["volts", "amps"])
    keys = set(model.transfer_state_dict())
    assert not any(k.startswith(("predictor.", "target.")) for k in keys)
    assert keys == set(StemTrunkEncoder(["volts", "amps"]).transfer_state_dict())

    path = tmp_path / "jepa.pt"
    save_transfer_checkpoint(path, model, objective="jepa", config={})
    rebuilt = build_encoder(load_transfer_checkpoint(path))
    for k, v in model.transfer_state_dict().items():
        assert torch.equal(rebuilt.state_dict()[k], v), k


def test_jepa_predictor_output_shape():
    from world_model.pretraining.jepa import JEPAPretrainModel
    model = JEPAPretrainModel(["volts", "amps"])
    out = model(torch.rand(2, 50, 2), torch.ones(2, 50, 2, dtype=torch.bool))
    assert out.shape == (2, 50, HIDDEN_DIM)


# ------------------------------------------------- JEPA training loop (C4)

def test_mask_contiguous_multi_block_exact_count_and_bounds():
    """n_blocks blocks, disjoint and non-touching, totalling within ratio_range."""
    mask = torch.ones(8, 200, 2, dtype=torch.bool)
    gen = torch.Generator().manual_seed(0)
    input_mask, hidden = mask_contiguous(mask, (0.40, 0.50), gen, n_blocks=4)
    for b in range(8):
        row = hidden[b].int()
        n_runs = int(((row[1:] - row[:-1]) == 1).sum()) + int(row[0])
        assert n_runs == 4, f"sample {b}: {n_runs} blocks"
        total = int(row.sum())
        assert 4 * (int(0.40 * 200) // 4) <= total <= int(0.50 * 200)
    assert not input_mask[hidden].any()
    assert input_mask[~hidden].all()


def test_jepa_training_loop_saves_contract_checkpoint(tmp_path):
    """The C4 seam test: a (tiny) JEPA training run must yield a checkpoint
    that round-trips through the contract and is indistinguishable from a
    masked-recon one except for objective='jepa'."""
    from world_model.pretraining.common import (
        build_encoder, load_transfer_checkpoint, save_transfer_checkpoint)
    from world_model.pretraining.jepa import evaluate, pretrain_jepa
    from world_model.data.windows import TrainWindows

    model, history = pretrain_jepa(
        _sessions(n=4), _sessions(n=2, seed=1), epochs=2,
        window=100, stride=100, batch_size=4, eval_every=10)
    assert len(history["loss"]) == 2
    assert all(np.isfinite(v) for v in history["loss"])

    val_ds = TrainWindows(_sessions(n=2, seed=1), window=100, stride=100,
                          channels=["volts", "amps"])
    m = evaluate(model, val_ds)
    assert m["embed_std"] > 1e-3, "embeddings collapsed to a constant"
    assert np.isfinite(m["latent_mse"])

    path = tmp_path / "jepa_c4.pt"
    save_transfer_checkpoint(path, model, objective="jepa", config={"epochs": 2})
    ckpt = load_transfer_checkpoint(path)
    assert ckpt["objective"] == "jepa"
    assert set(ckpt["transfer_state_dict"]) == \
        set(StemTrunkEncoder(["volts", "amps"]).transfer_state_dict())
    rebuilt = build_encoder(ckpt)
    for k, v in model.transfer_state_dict().items():
        assert torch.equal(rebuilt.state_dict()[k], v), k


def test_masked_recon_window_diet_trains_and_saves(tmp_path):
    """The control-group path: masked recon on the same TrainWindows diet
    must train (recon-only, no labels) and save through the same contract."""
    from world_model.pretraining.common import (
        load_transfer_checkpoint, save_transfer_checkpoint)
    from world_model.pretraining.masked_recon import (
        evaluate_windows, pretrain_windows)
    from world_model.data.windows import TrainWindows

    model, history = pretrain_windows(
        _sessions(n=4), _sessions(n=2, seed=1), epochs=2,
        window=100, stride=100, batch_size=4, eval_every=10)
    assert all(np.isfinite(v) for v in history["loss"])

    test_ds = TrainWindows(_sessions(n=2, seed=1), window=100, stride=100,
                           channels=["volts", "amps"])
    m = evaluate_windows(model, test_ds)
    assert np.isfinite(m["recon_mse"]) and m["recon_mse_mean_baseline"] > 0

    path = tmp_path / "mr_windows.pt"
    save_transfer_checkpoint(path, model, objective="masked_recon", config={})
    assert load_transfer_checkpoint(path)["objective"] == "masked_recon"


def test_deprecated_pretrain_polito_shim_still_exports():
    """The documented CLI/module path must keep working until callers migrate."""
    from world_model.training.pretrain_polito import (  # noqa: F401
        HIDDEN_DIM as shim_hidden, PolitoPretrainModel as shim_model)
    from world_model.pretraining.masked_recon import PolitoPretrainModel
    assert shim_model is PolitoPretrainModel and shim_hidden == HIDDEN_DIM
