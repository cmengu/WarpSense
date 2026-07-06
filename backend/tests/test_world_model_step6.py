"""
Step 6 (Gate 0.5) contract tests — Polito pre-training (STEPS.md).

Pins the transfer artifact's shape (what Step 8 will load), the masking
mechanics, and that a short run on real Polito welds actually learns —
recon better than the mean predictor, loss decreasing. Small slices of the
real CSVs keep this CPU-fast; the full run is the CLI's job.
"""

import pytest
import torch

from world_model.config import POLITO_DIR
from world_model.architecture.stems import STEM_DIM
from world_model.training.pretrain_polito import (
    HIDDEN_DIM,
    PRETRAIN_CHANNELS,
    PolitoPretrainModel,
    _mask_timesteps,
    _two_channel_batch,
    evaluate,
    pretrain,
)

pytestmark = pytest.mark.skipif(
    not (POLITO_DIR / "voltage.csv").exists(),
    reason="Polito dataset not downloaded (data/public/polito_rsw/)",
)


@pytest.fixture(scope="module")
def polito_sessions():
    from world_model.data.loader_polito import load_polito_sessions
    return load_polito_sessions(limit=60)


def test_transfer_artifact_contains_exactly_stems_and_trunk():
    model = PolitoPretrainModel()
    keys = set(model.transfer_state_dict())
    # every key belongs to the volts/amps stems or the trunk — heads excluded
    assert keys, "transfer artifact is empty"
    for k in keys:
        assert k.startswith(("stems.stems.volts.", "stems.stems.amps.", "trunk.")), k
    assert not any(k.startswith(("recon_head", "fault_head")) for k in keys)
    # both stems present (ChannelStems keyed by NAME — the D5 transfer mechanism)
    assert any("volts" in k for k in keys) and any("amps" in k for k in keys)


def test_trunk_weights_are_grucell_shaped():
    """Step 7's ODE-RNN encoder uses nn.GRUCell; the trunk must map onto it."""
    model = PolitoPretrainModel()
    sd = model.transfer_state_dict()
    cell = torch.nn.GRUCell(STEM_DIM, HIDDEN_DIM)
    assert sd["trunk.weight_ih_l0"].shape == cell.weight_ih.shape
    assert sd["trunk.weight_hh_l0"].shape == cell.weight_hh.shape
    assert sd["trunk.bias_ih_l0"].shape == cell.bias_ih.shape
    assert sd["trunk.bias_hh_l0"].shape == cell.bias_hh.shape


def test_mask_timesteps_hides_whole_frames():
    mask = torch.ones(4, 200, 2, dtype=torch.bool)
    gen = torch.Generator().manual_seed(0)
    input_mask, hidden = _mask_timesteps(mask, 0.15, gen)
    frac = hidden.float().mean()
    assert 0.05 < frac < 0.30  # ~15%, generous tolerance at this size
    # hidden frames are hidden across BOTH channels; visible frames untouched
    assert not input_mask[hidden].any()
    assert input_mask[~hidden].all()


def test_two_channel_batch_slices_volts_amps(polito_sessions):
    x, mask, fault = _two_channel_batch(polito_sessions[:8])
    assert x.shape[2] == len(PRETRAIN_CHANNELS) == 2
    assert mask.shape == x.shape and fault.shape == (8,)
    assert mask.any(), "no volts/amps present in real Polito welds?"
    assert float(x.min()) >= 0.0 and float(x.max()) <= 1.0  # pre-normalised [0,1]


def test_short_pretrain_learns_real_dynamics(polito_sessions):
    """Gate 0.5 in miniature: loss falls; recon beats the mean predictor."""
    train, val = polito_sessions[:40], polito_sessions[40:60]
    model, history = pretrain(train, val, epochs=3, batch_size=8,
                              seed=7, eval_every=100)
    assert history["loss"][-1] < history["loss"][0]
    m = evaluate(model, val, seed=7)
    assert m["recon_mse"] < m["recon_mse_mean_baseline"], (
        "recon no better than predicting the mean — Gate 0.5 kill criterion"
    )


def test_forward_shapes():
    model = PolitoPretrainModel()
    x = torch.rand(2, 50, 2)
    mask = torch.ones(2, 50, 2, dtype=torch.bool)
    out = model(x, mask)
    assert out["recon"].shape == (2, 50, 2)
    assert out["fault_logit"].shape == (2,)
