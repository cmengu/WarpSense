"""
STEPS.md Step 1 "done when": mock and Polito sessions round-trip through
SessionTensor with correct shapes/masks; splits are deterministic under SEED.
"""

import numpy as np
import pytest

from world_model.config import CHANNEL_INDEX, N_CHANNELS, POLITO_DIR, SEED
from world_model.data.loader_esp32 import load_esp32_sessions
from world_model.data.loader_mock import PARAMETRIC_ARC_TYPES, load_mock_corpus, load_mock_session
from world_model.data.loader_polito import load_polito_sessions
from world_model.data.schema import SessionTensor
from world_model.data.splits import split_sessions

polito_on_disk = pytest.mark.skipif(
    not (POLITO_DIR / "voltage.csv").exists(),
    reason="Polito dataset not downloaded",
)


def _tiny_session(session_id: str, **meta) -> SessionTensor:
    x = np.zeros((3, N_CHANNELS), dtype=np.float32)
    mask = np.zeros((3, N_CHANNELS), dtype=bool)
    return SessionTensor(x=x, mask=mask, meta={"session_id": session_id, "source": "mock", **meta})


# ---------------------------------------------------------------- schema

def test_schema_rejects_bad_shape_and_nonzero_masked():
    with pytest.raises(ValueError, match="x must be"):
        SessionTensor(x=np.zeros((5, 3)), mask=np.zeros((5, 3), dtype=bool),
                      meta={"session_id": "s", "source": "mock"})
    x = np.ones((5, N_CHANNELS), dtype=np.float32)
    with pytest.raises(ValueError, match="masked entries"):
        SessionTensor(x=x, mask=np.zeros_like(x, dtype=bool),
                      meta={"session_id": "s", "source": "mock"})
    with pytest.raises(ValueError, match="source"):
        _tiny_session("s").meta  # noqa — construction below is the real check
        SessionTensor(x=np.zeros((1, N_CHANNELS)), mask=np.zeros((1, N_CHANNELS), dtype=bool),
                      meta={"session_id": "s", "source": "not_a_source"})


# ---------------------------------------------------------------- mock loader

def test_mock_stitch_expert_round_trip():
    st = load_mock_session("stitch_expert", session_index=0)
    assert st.x.shape == (1500, N_CHANNELS)
    assert st.x.dtype == np.float32 and st.mask.dtype == bool
    assert (st.x[~st.mask] == 0.0).all()
    for name in ("volts", "amps", "angle_degrees"):
        assert st.mask[:, CHANNEL_INDEX[name]].any(), f"{name} never present"
    assert st.meta["source"] == "mock" and st.meta["quality_class"] == "GOOD"


def test_mock_mask_is_faithful_to_frames():
    # Round-trip fidelity: mask[t, c] must equal "the Frame had a value there".
    # (Checked against the frames themselves, not generator docstrings — the
    # novice docstring claims sparse thermal frames but the code emits every frame.)
    from data.mock_sessions import _generate_continuous_novice_frames
    from world_model.config import CHANNELS
    from world_model.data.schema import frames_to_session_tensor

    frames = _generate_continuous_novice_frames(0, 400)
    st = frames_to_session_tensor(frames, "roundtrip", "mock")
    for t, frame in enumerate(frames):
        for c, name in enumerate(CHANNELS):
            value = getattr(frame, name)
            assert st.mask[t, c] == (value is not None)
            if value is not None:
                assert st.x[t, c] == np.float32(value)
    # heat_diss is None on frame 0 (no previous temperature to difference) —
    # at least one masked entry must exist so the mask path is actually exercised
    assert not st.mask.all()


def test_mock_parametric_kinds_and_determinism():
    for kind in PARAMETRIC_ARC_TYPES:
        st = load_mock_session(kind, 7, num_frames=300)
        assert st.T == 300 and st.meta["kind"] == kind
    a = load_mock_session("al_cold", 7, num_frames=300)
    b = load_mock_session("al_cold", 7, num_frames=300)
    np.testing.assert_array_equal(a.x, b.x)
    corpus = load_mock_corpus(14, num_frames=200)
    assert len({s.session_id for s in corpus}) == 14


# ---------------------------------------------------------------- polito loader

@polito_on_disk
def test_polito_round_trip():
    sessions = load_polito_sessions(limit=25)
    assert len(sessions) > 0
    v, i = CHANNEL_INDEX["volts"], CHANNEL_INDEX["amps"]
    for st in sessions:
        assert st.x.shape == (st.T, N_CHANNELS) and st.T > 0
        # pre-normalised [0,1] — loader must NOT have rescaled (small slack for float noise)
        present = st.x[st.mask]
        assert present.min() >= -0.01 and present.max() <= 1.01
        assert st.mask[:, v].any() and st.mask[:, i].any()
        # the 4 channels Polito doesn't have are fully masked out
        for c in range(N_CHANNELS):
            if c not in (v, i):
                assert not st.mask[:, c].any()
        assert st.meta["fault"] in (0, 1)
        assert len(st.meta["force"]) == st.T
    assert len({s.session_id for s in sessions}) == len(sessions)


# ---------------------------------------------------------------- esp32 stub

def test_esp32_loader_fails_loudly():
    with pytest.raises(NotImplementedError, match="Gate 0"):
        load_esp32_sessions()


# ---------------------------------------------------------------- splits

def test_splits_deterministic_disjoint_and_proportional():
    sessions = [_tiny_session(f"sess_{i:04d}") for i in range(600)]
    s1 = split_sessions(sessions, seed=SEED)
    s2 = split_sessions(sessions, seed=SEED)
    ids = lambda split: [s.session_id for s in split]  # noqa: E731
    for name in ("train", "val", "test"):
        assert ids(s1[name]) == ids(s2[name])  # deterministic
    all_ids = ids(s1["train"]) + ids(s1["val"]) + ids(s1["test"])
    assert sorted(all_ids) == sorted(s.session_id for s in sessions)  # disjoint + complete
    assert 0.60 < len(s1["train"]) / 600 < 0.80
    assert len(s1["val"]) > 0 and len(s1["test"]) > 0
    # assignment is per-session, not positional: adding sessions must not move existing ones
    grown = split_sessions(sessions + [_tiny_session(f"new_{i}") for i in range(50)], seed=SEED)
    for name in ("train", "val", "test"):
        assert set(ids(s1[name])) <= set(ids(grown[name]))


def test_splits_ood_holdout():
    sessions = [_tiny_session(f"s{i}", thickness=(8.0 if i % 5 == 0 else 3.0)) for i in range(100)]
    out = split_sessions(sessions, ood_predicate=lambda m: m["thickness"] > 6.0)
    assert len(out["ood"]) == 20
    for name in ("train", "val", "test"):
        assert all(s.meta["thickness"] <= 6.0 for s in out[name])
