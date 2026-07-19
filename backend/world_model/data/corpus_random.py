"""
corpus_random.py builds the C8 CONTROL corpus: a spectrum-matched random
corpus that isolates *structure* from *volume* (C8 trap T4, decision D2,
ticket #23).

Why this exists — the trap it defuses:

  Moving from 1,976 Polito welds to ~20k simulated sessions is a 10× data
  increase, and synthetic-pretraining gains are frequently attributable to
  volume alone rather than to simulator fidelity (FlyingChairs: realism is not
  the axis that pays). Without a control, a win for the goldak corpus is
  unattributable — it could be structure OR it could just be more data.

  The control holds volume constant and removes structure. If goldak beats a
  corpus with the SAME per-channel power spectrum, the SAME frame count, and the
  SAME session count, then the win is structural, not spectral and not volume.
  The T4 detector (§7/TH2) reads exactly that margin.

Why spectrum-matched and NOT white noise (the whole point — D2):

  White noise is a trivially weak control: its power spectrum is flat, so any
  temporally structured corpus beats it and beating it proves almost nothing.
  A spectrum-matched control keeps the goldak corpus's *colored* per-channel
  power spectral density — its frequency content, and therefore (Wiener–Khinchin)
  its linear autocorrelation — while destroying the phase relationships that
  encode the physical waveform: the ramp-up after each arc start, the stitch
  dips, the coupling between channels. Same frequency content, same first two
  marginal moments, no causal or physical structure.

  The tool is Fourier phase randomisation (the "FT surrogate" of Theiler et al.
  1992). Per channel, per session:

      x[:, c]  ──rfft──▶  |X|·e^{iφ}
                          keep |X|            (power spectrum ↦ preserved exactly)
                          replace φ ← U(0,2π) (phase ↦ destroyed)
                          keep the DC bin real (mean ↦ preserved exactly)
               ◀─irfft──  a real signal, same PSD, scrambled phase

  Because |X| is preserved bin-for-bin, each surrogate session has EXACTLY the
  source session's per-channel power spectrum, so the corpus-averaged PSD matches
  to float round-off (verified per channel in test_c8_random_corpus.py). Mean and
  variance are preserved exactly (DC bin + Parseval); higher moments Gaussianise,
  which is inherent to a random-phase surrogate and is the intended behaviour for
  a *structure-free* control. (If exact marginals ever mattered, AAFT/IAAFT would
  rank-remap onto the source values at a small cost to the PSD match; D2 asks for
  the PSD match, so pure phase randomisation is the defensible reading.)

Identity and reproducibility (mirrors corpus_goldak.CorpusSpec):

  A RandomCorpusSpec is `source` (the CorpusSpec whose PSD is matched — goldak-wide
  by default, since T4 controls the goldak-wide arm) plus a `phase_seed`. The whole
  thing regenerates bit-for-bit: the source sessions come from `source` exactly as
  corpus_goldak produces them, and session i's phases are drawn from a numpy
  Generator seeded `phase_seed + i`. Session ids are `{name}_{i:06d}`, so growing
  the corpus leaves earlier sessions untouched and splits.py (which hashes the id)
  never moves a session between folds.

Caveat carried from the simulator (C8 trap T1): every number here descends from a
simulated number, twice removed (simulated, then phase-scrambled). It is a control,
never a source of a reported metric on its own.
"""

import hashlib
import json
from dataclasses import dataclass, field

import numpy as np

from world_model.config import N_CHANNELS, SEED
from world_model.data.corpus_goldak import GOLDAK_WIDE, CorpusSpec, generate_corpus, resolve_spec
from world_model.data.schema import SessionTensor

# The control matches goldak-wide (the arm T4 is about). A different base seed
# for the phases keeps them independent of the source draws while staying pinned.
DEFAULT_PHASE_SEED = SEED


@dataclass(frozen=True)
class RandomCorpusSpec:
    """Everything needed to regenerate the spectrum-matched control bit-for-bit.

    `source` is the CorpusSpec whose per-channel PSD is matched (its size and
    frame count also fix the control's shape and volume — a matched control).
    `phase_seed` is the base seed for phase randomisation: session i draws its
    phases from `phase_seed + i`, independent of the source's own seed so the
    two never collide.
    """

    name: str = "random-spectrum"
    source: CorpusSpec = GOLDAK_WIDE
    phase_seed: int = DEFAULT_PHASE_SEED

    def as_dict(self) -> dict:
        """JSON-ready manifest form (source nested as its own dict)."""
        return {
            "name": self.name,
            "source": self.source.as_dict(),
            "phase_seed": self.phase_seed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RandomCorpusSpec":
        """Inverse of as_dict(): rebuild a spec from a persisted manifest."""
        return cls(
            name=d["name"],
            source=CorpusSpec.from_dict(d["source"]),
            phase_seed=int(d["phase_seed"]),
        )

    def fingerprint(self) -> str:
        """Short stable hash of the manifest — the control's identity in runs.csv.

        Two random corpora share a fingerprint iff they match the same source PSD
        with the same phases, i.e. would generate the same sessions value-for-value.
        """
        blob = json.dumps(self.as_dict(), sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:12]

    @property
    def n_sessions(self) -> int:
        return self.source.n_sessions

    @property
    def n_frames(self) -> int:
        return self.source.n_frames

    def session_id(self, i: int) -> str:
        return f"{self.name}_{i:06d}"

    def phase_seed_for(self, i: int) -> int:
        return self.phase_seed + i


def resolve_random_spec(n_sessions: int | None = None, source_seed: int | None = None,
                        n_frames: int | None = None,
                        phase_seed: int | None = None) -> RandomCorpusSpec:
    """Build a RandomCorpusSpec matched to a goldak-wide source of the given size.

    The control always tracks goldak-wide (the arm T4 controls). Overriding the
    size/frames/seed flows through to the source spec — a 12-session control is
    matched to the 12-session goldak-wide corpus, which is what a smoke run wants;
    it produces a different fingerprint, correctly, because it is a different corpus.
    """
    source = resolve_spec("wide", n_sessions=n_sessions, seed=source_seed, n_frames=n_frames)
    return RandomCorpusSpec(
        source=source,
        phase_seed=DEFAULT_PHASE_SEED if phase_seed is None else phase_seed,
    )


def phase_randomise(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Phase-randomise every channel of a [T, C] real signal, PSD preserved.

    Per channel: keep the magnitude spectrum |rfft(x)| exactly, replace the phase
    of every non-DC (and, for even T, non-Nyquist) bin with a fresh uniform draw,
    then irfft back to a real length-T signal. The DC bin is kept as the original
    real value so the channel MEAN is preserved exactly; the magnitudes are kept
    bin-for-bin so the POWER SPECTRUM (hence the variance, by Parseval) is
    preserved exactly. Only the phase — the physical/causal waveform shape — is
    destroyed.
    """
    x = np.asarray(x, dtype=np.float64)
    T, C = x.shape
    out = np.empty((T, C), dtype=np.float64)
    for c in range(C):
        spectrum = np.fft.rfft(x[:, c])
        mag = np.abs(spectrum)
        phases = rng.uniform(0.0, 2.0 * np.pi, size=spectrum.shape[0])
        randomised = mag * np.exp(1j * phases)
        # DC bin real → mean preserved exactly.
        randomised[0] = spectrum[0].real
        # Even-length signals have a real Nyquist bin; keep it real (any imaginary
        # part there would be dropped by irfft and quietly change the power).
        if T % 2 == 0:
            randomised[-1] = mag[-1]
        out[:, c] = np.fft.irfft(randomised, n=T)
    return out


def _random_session(source: SessionTensor, spec: RandomCorpusSpec, i: int) -> SessionTensor:
    """One spectrum-matched surrogate of a source session (all 6 channels present).

    goldak sessions carry a full availability mask (every channel present every
    frame), so phase randomisation runs over the whole [T, 6] array with nothing
    to route around. The surrogate carries NO fusion-depth label: it descends from
    a scrambled signal, so any physical label would be a fiction — and the SSL
    objectives this control feeds (masked-recon, JEPA) never read one.
    """
    xr = phase_randomise(source.x, np.random.default_rng(spec.phase_seed_for(i)))
    meta = {
        "session_id": spec.session_id(i),
        "source": "goldak",          # lineage: a (scrambled) simulated signal
        "corpus": spec.name,
        "kind": "spectrum_surrogate",
        "source_session_id": source.session_id,
    }
    return SessionTensor(x=xr.astype(np.float32),
                         mask=np.ones_like(xr, dtype=bool), meta=meta)


def generate_random_corpus(spec: RandomCorpusSpec) -> list[SessionTensor]:
    """Generate the source corpus, then return its per-session spectrum-matched
    surrogates in order. Deterministic from the spec (source seed + phase seed)."""
    source_sessions = generate_corpus(spec.source)
    return [_random_session(s, spec, i) for i, s in enumerate(source_sessions)]


def load_random_sessions(n_sessions: int | None = None, source_seed: int | None = None,
                         n_frames: int | None = None,
                         phase_seed: int | None = None) -> tuple[list[SessionTensor], RandomCorpusSpec]:
    """Convenience for CLIs: (sessions, spec) for the spectrum-matched control.

    Returns the spec alongside the data so the caller can record the fingerprint
    (and the source it matched) in its run config without rebuilding them.
    """
    spec = resolve_random_spec(n_sessions=n_sessions, source_seed=source_seed,
                               n_frames=n_frames, phase_seed=phase_seed)
    return generate_random_corpus(spec), spec


# --------------------------------------------------------------- PSD diagnostics
#
# One-sided per-channel power spectral density, averaged over the sessions of a
# corpus. Used by the T4 verification test to assert the control matches goldak's
# spectrum per channel, and by anyone who wants to SEE that neither spectrum is
# flat (i.e. that the control is not white noise).

def channel_psd(session: SessionTensor) -> np.ndarray:
    """One-sided periodogram of each channel: |rfft(x)|^2 / T, shape [F, C]."""
    x = np.asarray(session.x, dtype=np.float64)
    T = x.shape[0]
    return (np.abs(np.fft.rfft(x, axis=0)) ** 2) / T


def corpus_psd(sessions: list[SessionTensor]) -> np.ndarray:
    """Per-channel PSD averaged across a corpus, shape [F, C].

    Every session must share the frame count (they do within one corpus), so the
    periodograms are all [F, C] and the mean is well defined.
    """
    if not sessions:
        raise ValueError("cannot compute a corpus PSD over zero sessions")
    return np.mean([channel_psd(s) for s in sessions], axis=0)
