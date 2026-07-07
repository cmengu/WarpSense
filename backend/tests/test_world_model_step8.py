"""
Step 8 contract tests — training loop (STEPS.md).

The load-bearing pins: symlog/symexp invert each other (consumers rely on
symexp to get real units back), the free-nats floor actually kills the KL
gradient below 1 nat (the posterior-collapse guard), the fade schedule turns
losses on in the pre-registered ORDER (recon → aux → physics → quality), the
Polito warm start lands in the assembled WeldWorldModel (D5), and one short
training run on a tiny mock batch drives recon DOWN (the Step 8 done-when,
plumbing-scale — D4).
"""

import pytest
import torch

from world_model.config import N_FEATURES
from world_model.architecture.encoder import HIDDEN_DIM
from world_model.architecture.world_model import WeldWorldModel
from world_model.data.batch import collate_sessions
from world_model.data.loader_mock import load_mock_session
from world_model.training.losses import (
    KL_WEIGHT,
    SCHEDULE,
    LossTerms,
    compute_losses,
    fade,
    total_loss,
)
from world_model.training.symlog import (
    FREE_NATS,
    PercentileNorm,
    free_nats_kl,
    symexp,
    symlog,
)
from world_model.training.train import load_polito_transfer, train

B, T = 2, 40  # tiny: adjoint dopri5 through the full graph must stay CPU-fast


@pytest.fixture(scope="module")
def mock_sessions():
    return [load_mock_session("stitch_expert", 0, num_frames=T),
            load_mock_session("al_defective", 1, num_frames=T)]


def test_symlog_symexp_are_inverses():
    x = torch.linspace(-1e4, 1e4, 101)
    assert torch.allclose(symexp(symlog(x)), x, rtol=1e-4)
    assert torch.allclose(symlog(-x), -symlog(x))          # odd symmetry
    assert symlog(torch.tensor(1e4)) < 10                  # compression happens


def test_free_nats_floor_kills_gradient_below_one_nat():
    # Posterior ≈ prior → KL below the floor: value clamps to FREE_NATS, grad dies
    mu = torch.zeros(B, 8, requires_grad=True)
    kl = free_nats_kl(mu, torch.zeros(B, 8))
    assert float(kl.detach()) == pytest.approx(FREE_NATS)
    kl.backward()
    assert torch.all(mu.grad == 0)
    # Posterior far from prior → above the floor, gradient flows
    mu2 = torch.full((B, 8), 3.0, requires_grad=True)
    kl2 = free_nats_kl(mu2, torch.zeros(B, 8))
    assert float(kl2) > FREE_NATS
    kl2.backward()
    assert torch.any(mu2.grad != 0)


def test_fade_schedule_order():
    """The pre-registered switch-on order: aux (0–100) before physics (50–150)
    before quality (150–250); each ramp is ~0 at start, ~1 at end, monotone."""
    for start, end in ((0, 100), (50, 150), (150, 250)):
        assert fade(start, start, end) < 0.01
        assert fade(end, start, end) > 0.99
        vals = [fade(e, start, end) for e in range(start, end + 1, 10)]
        assert all(a <= b for a, b in zip(vals, vals[1:]))
    epoch = 75  # mid-run: aux mostly on, physics partial, quality still off
    assert fade(epoch, 0, 100) > fade(epoch, 50, 150) > fade(epoch, 150, 250)


def test_total_loss_schedule_endpoints():
    one = torch.ones(())
    L = LossTerms(recon=one, physics=one, quality=one, aux=one, kl=one)
    early = float(total_loss(L, epoch=0))
    late = float(total_loss(L, epoch=300))
    # epoch 0: recon + kl only (all fades ≈ 0, aux ramp barely started)
    assert early == pytest.approx(1.0 + KL_WEIGHT, abs=0.05)
    # epoch 300: every term fully on
    full = 1.0 + KL_WEIGHT + sum(w for w, _, _ in SCHEDULE.values())
    assert late == pytest.approx(full, abs=0.01)


def test_percentile_norm_only_scales_down():
    norm = PercentileNorm()
    small = norm(torch.tensor(0.5))
    assert float(small) == pytest.approx(0.5)  # range < 1 → untouched
    for v in range(100):
        norm(torch.tensor(float(v)))
    assert float(norm(torch.tensor(50.0))) < 50.0  # wide range → scaled down
    scaled = norm(torch.tensor(1.0, requires_grad=True))
    scaled.backward()  # gradient survives the scaling


def test_compute_losses_terms_finite_and_grads_reach_all_components(mock_sessions):
    torch.manual_seed(0)
    batch = collate_sessions(mock_sessions)
    model = WeldWorldModel()
    model.fit_normalizer(mock_sessions)
    model.train()
    feats = torch.randn(B, N_FEATURES)
    out = model(batch.x, batch.mask, feats=feats)
    L = compute_losses(model, out, batch, target_mask=batch.mask,
                       feats_target=feats, feats_valid=torch.ones(B, dtype=torch.bool))
    for name, term in L.detached().items():
        assert term == term and abs(term) < 1e6, f"{name} not finite: {term}"
    total_loss(L, epoch=300).backward()  # epoch 300: every term contributes
    for name, module in [("stems", model.stems), ("encoder", model.encoder),
                         ("odefunc", model.odefunc), ("decoder", model.decoder)]:
        grads = [p.grad for p in module.parameters()]
        assert any(g is not None and g.abs().sum() > 0 for g in grads), (
            f"no gradient reached {name}")


def test_polito_warm_start_lands_in_world_model():
    """D5 end-to-end: transfer artifact → assembled model, stems AND trunk."""
    from world_model.training.pretrain_polito import PolitoPretrainModel
    sd = PolitoPretrainModel(hidden_dim=HIDDEN_DIM).transfer_state_dict()
    model = WeldWorldModel()
    loaded = load_polito_transfer(model, sd)
    assert set(loaded) == {"encoder.cell", "stems.volts", "stems.amps"}
    assert torch.equal(model.encoder.cell.weight_ih, sd["trunk.weight_ih_l0"])
    assert torch.equal(model.stems.stems["volts"].weight, sd["stems.stems.volts.weight"])
    assert torch.equal(model.stems.stems["amps"].bias, sd["stems.stems.amps.bias"])
    # untouched channels stay random-init (nothing to transfer)
    assert "stems.stems.travel_speed_mm_per_min.weight" not in sd


def test_short_training_run_decreases_recon(tmp_path, mock_sessions):
    """The Step 8 done-when at plumbing scale: a few epochs on a tiny mock
    corpus, recon trends down. Mock, so a wiring check, never a result (D4)."""
    corpus = [load_mock_session(kind, i, num_frames=T)
              for i, kind in enumerate(["stitch_expert", "continuous_novice",
                                        "al_nominal", "al_cold", "al_defective",
                                        "al_hot_clean"])]
    model, history = train(corpus, val_sessions=mock_sessions, epochs=4,
                           batch_size=3, eval_every=10, seed=0,
                           runs_csv=tmp_path / "runs.csv")
    assert len(history["recon"]) == 4
    assert history["recon"][-1] < history["recon"][0]
    assert all(v == v for v in history["loss"])  # no NaNs anywhere
