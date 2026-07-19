"""Tests for C8 ticket #21 — simulated-corpus pretraining behind --corpus.

Four things must hold at once:
  1. A corpus is an identity, not a pile of arrays: the same CorpusSpec always
     regenerates the same sessions, value for value, and a manifest written to
     disk round-trips back into the spec that produced them.
  2. goldak-wide and goldak-narrow differ in exactly one thing — the ranges —
     so the T3 under-randomisation detector compares corpora, not seeds.
  3. Splits are by whole session via the existing salted-hash splitter: no
     session id appears in two folds.
  4. `--corpus goldak` runs end to end on both objectives and leaves a
     checkpoint that loads through pretraining/common.load_transfer_checkpoint,
     while `--corpus polito` (the default) adds nothing to the run config — the
     C4-C7 reproductions must keep their config hashes.

Corpus sizes here are tiny (a dozen short sessions); the 20k default is a
production number and simulate_session is a per-frame Python loop.
"""

import json

import pytest
import torch

from world_model.architecture.trunk import TRANSFER_PREFIXES
from world_model.data.corpus_goldak import (
    GOLDAK_NARROW,
    GOLDAK_WIDE,
    CorpusSpec,
    generate_corpus,
    load_corpus_manifest,
    load_goldak_sessions,
    resolve_spec,
    save_corpus_manifest,
    thickness_ood_predicate,
)
from world_model.data.splits import split_sessions
from world_model.data.windows import TrainWindows
from world_model.pretraining.common import build_encoder, load_transfer_checkpoint
from world_model.pretraining.masked_recon import PRETRAIN_CHANNELS
from world_model.simulator.weld_sim import LEGACY_RANGES, WIDE_RANGES


def tiny_spec(variant: str = "wide", n_sessions: int = 6) -> CorpusSpec:
    """A corpus small and short enough to simulate inside a unit test."""
    return resolve_spec(variant, n_sessions=n_sessions, n_frames=400)


# --- 1. regenerable bit-for-bit from (seed, ranges) --------------------------

def test_same_spec_regenerates_identical_sessions():
    spec = tiny_spec(n_sessions=4)
    a = generate_corpus(spec)
    b = generate_corpus(spec)
    assert [s.session_id for s in a] == [s.session_id for s in b]
    for sa, sb in zip(a, b):
        assert (sa.x == sb.x).all()
        assert (sa.meta["fusion_depth_mm"] == sb.meta["fusion_depth_mm"]).all()


def test_growing_a_corpus_leaves_earlier_sessions_untouched():
    small = generate_corpus(tiny_spec(n_sessions=3))
    large = generate_corpus(tiny_spec(n_sessions=6))
    for sa, sb in zip(small, large):
        assert sa.session_id == sb.session_id
        assert (sa.x == sb.x).all()


def test_manifest_round_trips_and_pins_seed_and_ranges(tmp_path):
    spec = tiny_spec(n_sessions=3)
    path = save_corpus_manifest(spec, corpus_dir=tmp_path)
    payload = json.loads(path.read_text())
    assert payload["seed"] == spec.seed
    assert payload["ranges"]["name"] == "wide_c8"

    restored = load_corpus_manifest(path)
    assert restored == spec
    assert restored.fingerprint() == spec.fingerprint()
    for sa, sb in zip(generate_corpus(spec), generate_corpus(restored)):
        assert (sa.x == sb.x).all()


def test_fingerprint_tracks_every_field_that_changes_the_data():
    base = tiny_spec(n_sessions=3)
    assert base.fingerprint() != tiny_spec("narrow", n_sessions=3).fingerprint()
    assert base.fingerprint() != tiny_spec(n_sessions=4).fingerprint()
    assert base.fingerprint() == tiny_spec(n_sessions=3).fingerprint()


# --- 2. the T3 pair differs only in its ranges ------------------------------

def test_wide_and_narrow_differ_only_in_ranges():
    assert GOLDAK_WIDE.ranges is WIDE_RANGES
    assert GOLDAK_NARROW.ranges is LEGACY_RANGES
    assert (GOLDAK_WIDE.seed, GOLDAK_WIDE.n_sessions, GOLDAK_WIDE.n_frames) == \
           (GOLDAK_NARROW.seed, GOLDAK_NARROW.n_sessions, GOLDAK_NARROW.n_frames)


def test_narrow_corpus_has_one_noise_signature_and_wide_does_not():
    """The exact axis T3 is about: pre-#19 ranges leave noise a single point."""
    narrow = generate_corpus(tiny_spec("narrow", n_sessions=5))
    wide = generate_corpus(tiny_spec("wide", n_sessions=5))
    narrow_noise = {tuple(sorted(s.meta["params"]["noise"].items())) for s in narrow}
    wide_noise = {tuple(sorted(s.meta["params"]["noise"].items())) for s in wide}
    assert len(narrow_noise) == 1
    assert len(wide_noise) == 5


def test_sessions_record_the_ranges_that_produced_them():
    for s in generate_corpus(tiny_spec(n_sessions=2)):
        assert s.meta["params"]["ranges"]["name"] == "wide_c8"
        assert s.meta["corpus"] == "goldak-wide"
        assert s.meta["source"] == "goldak"


def test_unknown_variant_is_rejected():
    with pytest.raises(ValueError, match="unknown corpus variant"):
        resolve_spec("widest")


# --- 3. session-grouped splits, no leakage ----------------------------------

def test_splits_are_by_session_with_no_id_in_two_folds():
    sessions, _ = load_goldak_sessions(n_sessions=40, n_frames=200)
    splits = split_sessions(sessions)
    folds = {k: {s.session_id for s in v} for k, v in splits.items()}
    assert sum(len(v) for v in folds.values()) == len(sessions)
    seen = set()
    for ids in folds.values():
        assert not (seen & ids)
        seen |= ids
    assert folds["train"] and folds["val"] and folds["test"]


def test_ood_predicate_reserves_thickness_extremes():
    sessions, _ = load_goldak_sessions(n_sessions=30, n_frames=200)
    splits = split_sessions(sessions, ood_predicate=thickness_ood_predicate(4.0, 9.0))
    for s in splits["ood"]:
        assert not 4.0 <= s.meta["params"]["plate_thickness_mm"] <= 9.0
    for name in ("train", "val", "test"):
        for s in splits[name]:
            assert 4.0 <= s.meta["params"]["plate_thickness_mm"] <= 9.0


# --- 4. both objectives train on it and the checkpoint round-trips ----------

def _run_cli(module_main, argv, monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", argv)
    module_main()


@pytest.mark.parametrize("module_name,objective", [
    ("world_model.pretraining.masked_recon", "masked_recon"),
    ("world_model.pretraining.jepa", "jepa"),
])
def test_corpus_goldak_run_yields_a_loadable_transfer_checkpoint(
        module_name, objective, tmp_path, monkeypatch):
    import importlib

    module = importlib.import_module(module_name)
    monkeypatch.setattr(module, "CHECKPOINTS_DIR", tmp_path)
    saved = {}

    def fake_append_run(*args, **kwargs):
        saved["config"] = args[1]
        return "testhash"

    import world_model.eval.eval_world_model as ewm
    monkeypatch.setattr(ewm, "append_run", fake_append_run)

    _run_cli(module.main, [
        module_name, "--corpus", "goldak", "--corpus-sessions", "6",
        "--epochs", "1", "--window", "150", "--stride", "75"], monkeypatch)

    ckpt_path = tmp_path / f"{'masked_recon_windows' if objective == 'masked_recon' else 'jepa_pretrain'}_testhash.pt"
    ckpt = load_transfer_checkpoint(ckpt_path)
    assert ckpt["objective"] == objective
    assert ckpt["channels"] == PRETRAIN_CHANNELS
    assert all(k.startswith(TRANSFER_PREFIXES) for k in ckpt["transfer_state_dict"])
    assert ckpt["config"]["corpus"] == "goldak-wide"
    assert ckpt["config"]["corpus_seed"] == 1337

    # the rebuilt encoder is usable: it consumes the same 2-channel windows
    encoder = build_encoder(ckpt)
    sessions, _ = load_goldak_sessions(n_sessions=1, n_frames=200)
    ds = TrainWindows(sessions, window=150, stride=75, channels=PRETRAIN_CHANNELS)
    x, mask = ds[0]
    out = encoder.encode(x.unsqueeze(0), mask.unsqueeze(0))
    assert out.shape == (1, 150, ckpt["hidden_dim"])
    assert torch.isfinite(out).all()


def test_corpus_variant_narrow_runs_and_records_its_name(tmp_path, monkeypatch):
    """The T3 detector compares masked-recon checkpoints from the wide vs the
    narrow corpus, so a --corpus-variant narrow run must go end to end and stamp
    its corpus name into the config that names the checkpoint."""
    import world_model.pretraining.masked_recon as module

    monkeypatch.setattr(module, "CHECKPOINTS_DIR", tmp_path)
    saved = {}

    def fake_append_run(*args, **kwargs):
        saved["config"] = args[1]
        return "narrowhash"

    import world_model.eval.eval_world_model as ewm
    monkeypatch.setattr(ewm, "append_run", fake_append_run)

    _run_cli(module.main, [
        "world_model.pretraining.masked_recon", "--corpus", "goldak",
        "--corpus-variant", "narrow", "--corpus-sessions", "6",
        "--epochs", "1", "--window", "150", "--stride", "75"], monkeypatch)

    assert saved["config"]["corpus"] == "goldak-narrow"
    ckpt = load_transfer_checkpoint(tmp_path / "masked_recon_windows_narrowhash.pt")
    assert ckpt["config"]["corpus"] == "goldak-narrow"


def test_polito_default_adds_nothing_to_the_run_config():
    """C4-C7 reproductions hash their config; a new key would rename every
    checkpoint. load_corpus must return empty extras on the default path."""
    from world_model.pretraining.masked_recon import load_corpus

    class Args:
        corpus = "polito"
        tiny = True
        limit = 4

    sessions, extras = load_corpus(Args())
    assert extras == {}
    assert sessions and sessions[0].meta["source"] == "polito"
