"""Tests for C8 ticket #23 — the spectrum-matched random control corpus (T4/D2).

Five things must hold at once for this corpus to be a MEANINGFUL control rather
than a trivial one:

  1. Per-channel PSD match. The whole point of D2: the control must carry the
     goldak-wide corpus's per-channel power spectral density, not a flat one. We
     verify the corpus-averaged PSD matches goldak's, per channel, within a tight
     tolerance (phase randomisation preserves the magnitude spectrum bin-for-bin,
     so the only error is float32 + irfft round-off).
  2. NOT white noise. A flat spectrum would make T4 meaningless. We verify both
     goldak's and the control's spectra are strongly colored (far from flat), and
     that the control is a poor match to the white-noise (flat) spectrum it must
     out-structure.
  3. Phases randomised / no causal structure. The surrogate must differ from its
     source in the time domain (phase destroyed) while matching it in magnitude.
  4. Marginal statistics preserved. Per-channel mean and variance carry over
     exactly (DC bin + Parseval), which is what "same marginal statistics" buys.
  5. Regenerable bit-for-bit from seed, and a manifest that round-trips.

Corpus sizes here are tiny (a handful of short sessions); the 20k default is a
production number and the source sessions are a per-frame Python loop.
"""

import json

import numpy as np
import pytest

from world_model.data.corpus_goldak import generate_corpus, resolve_spec
from world_model.data.corpus_random import (
    RandomCorpusSpec,
    channel_psd,
    corpus_psd,
    generate_random_corpus,
    load_random_sessions,
    phase_randomise,
    resolve_random_spec,
)
from world_model.data.splits import split_sessions
from world_model.config import N_CHANNELS


def tiny_spec(n_sessions: int = 6, n_frames: int = 512) -> RandomCorpusSpec:
    """A control small and short enough to build inside a unit test."""
    return resolve_random_spec(n_sessions=n_sessions, n_frames=n_frames)


# --- 1. per-channel PSD matches goldak-wide within tolerance (D2, the T4 test) ---

def test_corpus_psd_matches_the_goldak_source_per_channel():
    spec = tiny_spec(n_sessions=8, n_frames=512)
    control = generate_random_corpus(spec)
    goldak = generate_corpus(spec.source)

    p_control = corpus_psd(control)   # [F, C]
    p_goldak = corpus_psd(goldak)
    assert p_control.shape == p_goldak.shape
    assert p_control.shape[1] == N_CHANNELS

    # Per channel: relative L2 error over the spectrum. Phase randomisation keeps
    # each session's magnitude spectrum exactly, so the averaged PSD matches to
    # float32/irfft round-off. Tolerance: 1e-3 relative, per channel.
    for c in range(N_CHANNELS):
        num = np.linalg.norm(p_control[:, c] - p_goldak[:, c])
        den = np.linalg.norm(p_goldak[:, c])
        rel = num / den
        assert rel < 1e-3, f"channel {c}: PSD relative error {rel:.2e} exceeds 1e-3"


def test_per_session_magnitude_spectrum_is_preserved_exactly():
    """Phase randomisation must leave |rfft| alone (only the phase moves)."""
    spec = tiny_spec(n_sessions=3, n_frames=512)
    control = generate_random_corpus(spec)
    goldak = generate_corpus(spec.source)
    for cs, gs in zip(control, goldak):
        mag_c = np.abs(np.fft.rfft(cs.x, axis=0))
        mag_g = np.abs(np.fft.rfft(gs.x, axis=0))
        assert np.allclose(mag_c, mag_g, rtol=1e-4, atol=1e-3)


# --- 2. it is NOT white noise (the reason spectrum matching matters) ----------

def test_spectrum_is_strongly_colored_not_flat():
    """White noise has a flat PSD. Both goldak and its control must be far from
    flat — otherwise beating the control would prove nothing (D2)."""
    spec = tiny_spec(n_sessions=8, n_frames=512)
    p_control = corpus_psd(generate_random_corpus(spec))
    p_goldak = corpus_psd(generate_corpus(spec.source))
    # Coefficient of variation across frequency bins, per channel: ~0 for white
    # noise, large for a colored (structured) spectrum. Drop the DC bin, which is
    # just the mean and would swamp the comparison.
    for c in range(N_CHANNELS):
        for name, psd in (("goldak", p_goldak), ("control", p_control)):
            band = psd[1:, c]
            cov = band.std() / band.mean()
            assert cov > 1.0, f"{name} channel {c}: spectrum too flat (cov={cov:.2f})"


def test_control_does_not_match_a_white_noise_spectrum():
    """Sanity floor: the control's colored PSD is a POOR match to the flat
    spectrum it must out-structure — the mistake this ticket exists to avoid."""
    spec = tiny_spec(n_sessions=8, n_frames=512)
    p_control = corpus_psd(generate_random_corpus(spec))
    for c in range(N_CHANNELS):
        band = p_control[1:, c]
        flat = np.full_like(band, band.mean())   # a white-noise PSD of equal power
        rel = np.linalg.norm(band - flat) / np.linalg.norm(band)
        assert rel > 0.5, f"channel {c}: control PSD is suspiciously flat (rel={rel:.2f})"


# --- 3. phases randomised, no causal structure retained ----------------------

def test_surrogate_differs_from_source_in_the_time_domain():
    spec = tiny_spec(n_sessions=4, n_frames=512)
    control = generate_random_corpus(spec)
    goldak = generate_corpus(spec.source)
    for cs, gs in zip(control, goldak):
        # Same magnitude spectrum, but the waveform itself is scrambled: the two
        # signals must not be close anywhere (phase carries the shape).
        assert not np.allclose(cs.x, gs.x, atol=1e-2)


def test_phase_randomise_preserves_mean_and_variance_per_channel():
    """Marginal statistics (first two moments) carry over exactly."""
    rng = np.random.default_rng(0)
    x = rng.standard_normal((512, N_CHANNELS)).cumsum(axis=0)  # colored, nonzero mean
    y = phase_randomise(x, np.random.default_rng(123))
    assert np.allclose(x.mean(axis=0), y.mean(axis=0), atol=1e-6)
    assert np.allclose(x.var(axis=0), y.var(axis=0), rtol=1e-6)
    # and the magnitude spectrum is untouched
    assert np.allclose(np.abs(np.fft.rfft(x, axis=0)), np.abs(np.fft.rfft(y, axis=0)),
                       rtol=1e-6, atol=1e-6)


def test_phase_randomise_is_real_and_finite_for_odd_and_even_lengths():
    rng = np.random.default_rng(1)
    for T in (511, 512):
        x = rng.standard_normal((T, N_CHANNELS))
        y = phase_randomise(x, np.random.default_rng(7))
        assert y.shape == (T, N_CHANNELS)
        assert np.isfinite(y).all()
        assert np.isrealobj(y)


# --- 4. sessions are well-formed and carry no fictional label ----------------

def test_sessions_are_goldak_lineage_labelled_control_with_no_depth():
    for s in generate_random_corpus(tiny_spec(n_sessions=3)):
        assert s.meta["source"] == "goldak"
        assert s.meta["corpus"] == "random-spectrum"
        assert s.meta["kind"] == "spectrum_surrogate"
        assert "fusion_depth_mm" not in s.meta   # scrambled signal → no real label
        assert s.mask.all()                       # full availability, like goldak


# --- 5. regenerable bit-for-bit, manifest round-trips ------------------------

def test_same_spec_regenerates_identical_sessions():
    spec = tiny_spec(n_sessions=4)
    a = generate_random_corpus(spec)
    b = generate_random_corpus(spec)
    assert [s.session_id for s in a] == [s.session_id for s in b]
    for sa, sb in zip(a, b):
        assert (sa.x == sb.x).all()


def test_growing_the_control_leaves_earlier_sessions_untouched():
    small = generate_random_corpus(tiny_spec(n_sessions=3))
    large = generate_random_corpus(tiny_spec(n_sessions=6))
    for sa, sb in zip(small, large):
        assert sa.session_id == sb.session_id
        assert (sa.x == sb.x).all()


def test_different_phase_seed_changes_the_sessions_but_not_the_psd():
    a = resolve_random_spec(n_sessions=5, n_frames=512, phase_seed=1)
    b = resolve_random_spec(n_sessions=5, n_frames=512, phase_seed=2)
    sa, sb = generate_random_corpus(a), generate_random_corpus(b)
    assert not (sa[0].x == sb[0].x).all()          # different phases
    # ...but the PSD is fixed by the shared source, so it still matches
    for c in range(N_CHANNELS):
        pa, pb = corpus_psd(sa)[:, c], corpus_psd(sb)[:, c]
        assert np.linalg.norm(pa - pb) / np.linalg.norm(pb) < 1e-3


def test_manifest_round_trips_and_pins_source_and_phase_seed():
    spec = tiny_spec(n_sessions=3)
    payload = json.loads(json.dumps(spec.as_dict(), sort_keys=True))
    assert payload["name"] == "random-spectrum"
    assert payload["phase_seed"] == spec.phase_seed
    assert payload["source"]["ranges"]["name"] == "wide_c8"

    restored = RandomCorpusSpec.from_dict(payload)
    assert restored == spec
    assert restored.fingerprint() == spec.fingerprint()
    for sa, sb in zip(generate_random_corpus(spec), generate_random_corpus(restored)):
        assert (sa.x == sb.x).all()


def test_fingerprint_tracks_every_field_that_changes_the_data():
    base = tiny_spec(n_sessions=3)
    assert base.fingerprint() == tiny_spec(n_sessions=3).fingerprint()
    assert base.fingerprint() != tiny_spec(n_sessions=4).fingerprint()
    assert base.fingerprint() != resolve_random_spec(
        n_sessions=3, n_frames=512, phase_seed=999).fingerprint()


# --- 6. splits are by whole session, no leakage ------------------------------

def test_splits_are_by_session_with_no_id_in_two_folds():
    sessions, _ = load_random_sessions(n_sessions=40, n_frames=256)
    splits = split_sessions(sessions)
    folds = {k: {s.session_id for s in v} for k, v in splits.items()}
    assert sum(len(v) for v in folds.values()) == len(sessions)
    seen = set()
    for ids in folds.values():
        assert not (seen & ids)
        seen |= ids
    assert folds["train"] and folds["val"] and folds["test"]


def test_corpus_psd_rejects_an_empty_corpus():
    with pytest.raises(ValueError, match="zero sessions"):
        corpus_psd([])
