"""
STEPS.md Step 3 "done when": harness produces a runs.csv row; GRU trains
end-to-end on mock; random-channel-dropout training works.
"""

import numpy as np
import pytest
import torch

from world_model.architecture.stems import ChannelStems, random_channel_dropout
from world_model.baselines.gru_baseline import GRUBaseline
from world_model.data.batch import collate_sessions
from world_model.data.loader_mock import load_mock_corpus
from world_model.eval.eval_world_model import RUNS_COLUMNS, append_run, evaluate
from world_model.training.train_gru import train_gru


@pytest.fixture(scope="module")
def tiny_corpus():
    return load_mock_corpus(21, num_frames=200)


# ---------------------------------------------------------------- stems

def test_stem_aggregation_is_mean_not_sum():
    # Embedding magnitude must NOT scale with sensor count (review fix #4):
    # feed identical values through 2 vs 6 channels; norms must be comparable.
    torch.manual_seed(0)
    stems = ChannelStems()
    x = torch.randn(1, 50, 6)
    full = torch.ones(1, 50, 6, dtype=torch.bool)
    two = torch.zeros_like(full)
    two[:, :, :2] = True
    n_full = stems(x, full).norm(dim=-1).mean()
    n_two = stems(x, two).norm(dim=-1).mean()
    assert n_two / n_full < 2.5, "sum-like scaling with channel count detected"


def test_stems_zero_channel_frames_guarded():
    stems = ChannelStems()
    x = torch.randn(2, 30, 6)
    mask = torch.zeros(2, 30, 6, dtype=torch.bool)
    mask[:, :10] = True  # last 20 frames have NO channels
    out = stems(x, mask)
    assert torch.isfinite(out).all()
    assert (out[:, 10:] == 0).all()


def test_channel_dropout_drops_whole_channels():
    mask = torch.ones(64, 20, 6, dtype=torch.bool)
    gen = torch.Generator().manual_seed(1)
    dropped = random_channel_dropout(mask, p=0.5, generator=gen)
    per_channel = dropped.reshape(64, 20, 6).all(dim=1) | ~dropped.reshape(64, 20, 6).any(dim=1)
    assert per_channel.all(), "dropout must remove whole channels, not single frames"
    assert not dropped.all() and dropped.any()


# ---------------------------------------------------------------- model + harness

def test_gru_forward_backward_shapes(tiny_corpus):
    model = GRUBaseline()
    model.fit_normalizer(tiny_corpus)
    batch = collate_sessions(tiny_corpus[:4])
    out = model(batch.x, batch.mask)
    assert out["quality_logits"].shape == (4, 3)
    assert out["depth_mm"].shape == (4,)
    out["quality_logits"].sum().backward()  # gradients flow through stems+trunk
    assert model.stems.stems["volts"].weight.grad is not None


def test_evaluate_and_runs_csv(tiny_corpus, tmp_path):
    model = GRUBaseline()
    model.fit_normalizer(tiny_corpus)
    metrics = evaluate(model, tiny_corpus)
    assert metrics["n"] == len(tiny_corpus)
    assert 0.0 <= metrics["quality_f1_macro"] <= 1.0
    assert set(metrics["per_class_recall"]) == {"GOOD", "MARGINAL", "DEFECTIVE"}
    assert metrics["fusion_mae_mm"] is None  # mock has no depth labels

    csv = tmp_path / "runs.csv"
    append_run("gru_baseline", {"a": 1}, 0, "val", metrics, note="t", runs_csv=csv)
    append_run("gru_baseline", {"a": 1}, 0, "test", metrics, runs_csv=csv)
    lines = csv.read_text().strip().splitlines()
    assert lines[0] == ",".join(RUNS_COLUMNS)
    assert len(lines) == 3 and all(len(l.split(",")) == len(RUNS_COLUMNS) for l in lines)


def test_gru_trains_end_to_end(tiny_corpus, tmp_path):
    # 3 epochs on 21×200-frame sessions — loss must drop and stay finite (CPU, seconds).
    # runs_csv redirected to tmp so test runs never pollute the real evidence file.
    train, val = tiny_corpus[:14], tiny_corpus[14:]
    model, history = train_gru(train, val, epochs=3, batch_size=4, eval_every=100,
                               runs_csv=tmp_path / "runs.csv")
    assert len(history["loss"]) == 3
    assert np.isfinite(history["loss"]).all()
    assert history["loss"][-1] < history["loss"][0]
