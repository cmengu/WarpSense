"""
Step 7 contract tests — world-model architecture (STEPS.md).

The load-bearing pins: the heat head's input dim is PHYS_DIMS=4 (the D6
grounding cannot silently regress), the ODE is CONTROLLED (editing u(t)
changes the trajectory from the same z0 — Gate 2's counterfactuals depend on
this), the encoder cell accepts the Step 6 Polito trunk, and a full
forward + backward runs on a tiny mock batch on CPU (the Step 7 done-when).
"""

import dataclasses

import pytest
import torch

from world_model.config import (
    CONTROL_CHANNELS,
    LATENT_DIM,
    N_FEATURES,
    PHYS_DIMS,
    QUALITY_CLASSES,
)
from world_model.architecture.decoder import WorldModelDecoder
from world_model.architecture.encoder import HIDDEN_DIM, ODERNNEncoder
from world_model.architecture.odefunc import (
    ControlledODEFunc,
    ControlSignal,
    integrate,
    physics_residual,
)
from world_model.architecture.stems import STEM_DIM
from world_model.architecture.world_model import WeldWorldModel
from world_model.data.batch import collate_sessions
from world_model.data.loader_mock import load_mock_session

B, T = 2, 40  # tiny: dopri5 through the full graph must stay CPU-fast


@pytest.fixture(scope="module")
def mock_batch():
    sessions = [load_mock_session("stitch_expert", 0, num_frames=T),
                load_mock_session("al_cold", 1, num_frames=T)]
    return sessions, collate_sessions(sessions)


def _control(seed: int = 0) -> ControlSignal:
    gen = torch.Generator().manual_seed(seed)
    controls = torch.rand(B, T, len(CONTROL_CHANNELS), generator=gen)
    t_grid = torch.arange(T, dtype=torch.float32) * 0.01
    return ControlSignal(controls, t_grid)


def test_heat_head_input_dim_is_phys_dims():
    """THE grounding pin: MLP_heat reads exactly z[:, :, :4], nothing more."""
    decoder = WorldModelDecoder()
    assert decoder.heat_head[0].in_features == PHYS_DIMS == 4
    # behavioural check: perturbing the free dims must not move heat_diss_hat
    z = torch.randn(B, T, LATENT_DIM)
    z_free_edit = z.clone()
    z_free_edit[:, :, PHYS_DIMS:] += 10.0
    out, out_edit = decoder(z), decoder(z_free_edit)
    assert torch.equal(out["heat_diss_hat"], out_edit["heat_diss_hat"])
    assert not torch.equal(out["depth_hat"], out_edit["depth_hat"])  # full-z heads do move


def test_decoder_head_shapes():
    decoder = WorldModelDecoder()
    out = decoder(torch.randn(B, T, LATENT_DIM), feats=torch.randn(B, N_FEATURES))
    assert out["heat_diss_hat"].shape == (B, T)
    assert out["other5_hat"].shape == (B, T, 5)
    assert out["depth_hat"].shape == (B, T)
    assert out["quality_logits"].shape == (B, len(QUALITY_CLASSES))
    assert out["feats_hat"].shape == (B, N_FEATURES)


def test_quality_head_fuses_the_11_features():
    """PHOENIX fusion: input dim = latent + 11; feats actually change the logits."""
    decoder = WorldModelDecoder()
    assert decoder.quality_head[0].in_features == LATENT_DIM + N_FEATURES
    z = torch.randn(B, T, LATENT_DIM)
    with_feats = decoder(z, feats=torch.ones(B, N_FEATURES))["quality_logits"]
    without = decoder(z, feats=None)["quality_logits"]  # None → zeros, still runs
    assert not torch.equal(with_feats, without)


def test_n_features_matches_the_real_extractor():
    """config.N_FEATURES pins SessionFeatures.to_vector() (11 engineered features)."""
    from warpsense.features.session_feature_extractor import SessionFeatures
    fields = {f.name for f in dataclasses.fields(SessionFeatures)}
    assert len(fields - {"session_id", "quality_label"}) == N_FEATURES


def test_ode_is_controlled_not_autonomous():
    """Same z0, edited u(t) → different trajectory. Gate 2 counterfactuals
    (Step 12) are architecturally possible only because this holds."""
    torch.manual_seed(0)
    odefunc = ControlledODEFunc()
    z0 = torch.randn(B, LATENT_DIM)
    control = _control(seed=0)
    t_grid = control.t_grid
    z_a = integrate(odefunc, z0, t_grid, control, adjoint=False)
    edited = ControlSignal(control.controls * 1.5, t_grid)  # e.g. crank amps/volts
    z_b = integrate(odefunc, z0, t_grid, edited, adjoint=False)
    assert z_a.shape == (B, T, LATENT_DIM)
    assert torch.allclose(z_a[:, 0], z_b[:, 0])          # same start
    assert not torch.allclose(z_a[:, -1], z_b[:, -1])    # different evolution


def test_control_signal_interpolates_between_frames():
    control = _control()
    t_grid = control.t_grid
    u_mid = control(t_grid[3] + 0.005)  # halfway between frames 3 and 4
    expected = 0.5 * (control.controls[:, 3] + control.controls[:, 4])
    assert torch.allclose(u_mid, expected, atol=1e-6)
    # clamped outside the grid, not extrapolated
    assert torch.allclose(control(t_grid[-1] + 1.0), control.controls[:, -1])
    assert torch.allclose(control(t_grid[0] - 1.0), control.controls[:, 0])


def test_physics_residual_is_finite_and_reaches_odefunc():
    torch.manual_seed(0)
    odefunc = ControlledODEFunc()
    z_traj = torch.randn(B, T, LATENT_DIM, requires_grad=True)
    loss = physics_residual(odefunc, z_traj, _control())
    assert loss.ndim == 0 and torch.isfinite(loss)
    loss.backward()
    assert odefunc.net[0].weight.grad is not None  # pressure lands on f_θ


def test_encoder_loads_polito_trunk():
    """The D5 warm start: Step 6's nn.GRU trunk maps onto the encoder's GRUCell."""
    from world_model.pretraining.masked_recon import PolitoPretrainModel
    pretrained = PolitoPretrainModel(hidden_dim=HIDDEN_DIM)
    sd = pretrained.transfer_state_dict()
    encoder = ODERNNEncoder()
    encoder.load_pretrained_trunk(sd)
    assert torch.equal(encoder.cell.weight_ih, sd["trunk.weight_ih_l0"])
    assert torch.equal(encoder.cell.weight_hh, sd["trunk.weight_hh_l0"])


def test_encoder_output_shapes_and_sampling():
    encoder = ODERNNEncoder()
    mu0, log_sigma0 = encoder(torch.randn(B, T, STEM_DIM), dt=0.01)
    assert mu0.shape == log_sigma0.shape == (B, LATENT_DIM)
    encoder.eval()
    assert torch.equal(encoder.sample_z0(mu0, log_sigma0), mu0)  # eval = posterior mean
    encoder.train()
    torch.manual_seed(0)
    assert not torch.equal(encoder.sample_z0(mu0, log_sigma0), mu0)


def test_forward_backward_on_tiny_mock_batch(mock_batch):
    """The Step 7 done-when: full model, forward + backward, one tiny CPU batch
    through the adjoint dopri5 path — gradients reach every component."""
    _, batch = mock_batch
    torch.manual_seed(0)
    model = WeldWorldModel()
    model.train()
    out = model(batch.x, batch.mask)
    loss = (out["heat_diss_hat"].pow(2).mean() + out["other5_hat"].pow(2).mean()
            + out["depth_hat"].pow(2).mean() + out["quality_logits"].pow(2).mean()
            + out["feats_hat"].pow(2).mean() + out["mu0"].pow(2).mean()
            + physics_residual(model.odefunc, out["z_traj"], out["control"]))
    loss.backward()
    for name, module in [("stems", model.stems), ("encoder", model.encoder),
                         ("odefunc", model.odefunc), ("decoder", model.decoder)]:
        grads = [p.grad for p in module.parameters()]
        assert any(g is not None and g.abs().sum() > 0 for g in grads), (
            f"no gradient reached {name}"
        )


def test_infer_protocol(mock_batch):
    """Eval surface mirrors GRUBaseline.predict; per-frame curves are new."""
    sessions, _ = mock_batch
    model = WeldWorldModel()
    model.fit_normalizer(sessions)
    out = model.infer(sessions[0])
    assert out["quality_probs"].shape == (len(QUALITY_CLASSES),)
    assert torch.allclose(out["quality_probs"].sum(), torch.tensor(1.0), atol=1e-5)
    assert out["depth_mm"].shape == (T,)
    assert out["z_traj"].shape == (T, LATENT_DIM)
    assert out["feats_hat"].shape == (N_FEATURES,)
