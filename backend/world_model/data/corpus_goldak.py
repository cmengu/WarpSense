"""
corpus_goldak.py turns the Goldak simulator into a PRETRAINING CORPUS: a named,
seeded, range-pinned collection of simulated arc-weld sessions that any
pretraining objective can train on instead of Polito (C8 §8 item 2, ticket #21).

Why a module rather than a one-line list comprehension over sample_params():

  1. A corpus is an experimental artifact, so it needs an identity. Two runs
     that both say "trained on Goldak" are only comparable if they drew the
     same sessions from the same distribution — and the only way to know that
     afterwards is if the run recorded WHICH corpus. CorpusSpec is that
     identity: name + seed + session count + frame count + RandomisationRanges.
  2. Corpora are big and cheap to recompute. 20k sessions × 1500 frames × 6
     channels is ~700 MB of float32 that regenerates deterministically from
     five numbers, so what gets persisted is the SPEC (a ~1 KB JSON manifest),
     not the arrays. "Regenerable bit-for-bit" is therefore a property of the
     manifest: same manifest → same sessions, value for value, on any machine.
  3. C8's trap T3 (under-randomisation) needs TWO corpora that differ in
     exactly one thing — the ranges. GOLDAK_WIDE and GOLDAK_NARROW below are
     that pair: identical seed, identical size, identical session ids, and the
     ONLY difference is WIDE_RANGES vs LEGACY_RANGES (the pre-#19 ranges).
     The T3 detector compares masked-recon checkpoints from the two.

For newcomers — how one corpus is built:

    CorpusSpec(name="goldak-wide", seed=1337, n_sessions=20000, ranges=WIDE)
        │  generate_corpus()
        │    session i:  seed_i = spec.seed + i
        │                params = sample_params(seed_i, id_i, ranges)
        │                session = simulate_session(params)
        ▼
    list[SessionTensor]  (source="goldak", 6 channels, fusion_depth_mm in meta)
        │  splits.split_sessions(seed=...)   ← the SAME salted-hash splitter
        ▼                                      Polito uses; whole sessions only
    {"train": [...], "val": [...], "test": [...], "ood": [...]}

Session ids are `{spec.name}_{i:06d}` and the per-session seed is `spec.seed + i`,
so growing a corpus from 1k to 20k sessions leaves the first 1k untouched — and
because splits.py hashes the session_id, growing it never moves an existing
session between folds either. Splitting is by SESSION, so no window of a weld
can appear in two folds (the leakage rule in splits.py).

Everything here is deterministic and free of global RNG use: simulate_session
seeds its own numpy Generator from SimParams.seed, and sample_params seeds its
own random.Random. Calling generate_corpus twice in one process gives identical
sessions; interleaving it with other seeded code perturbs neither.

Caveat carried from the simulator (C8 trap T1): every number produced from this
corpus is a simulated number. It is never reported alone.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from world_model.config import SEED
from world_model.data.schema import SessionTensor
from world_model.simulator.weld_sim import (
    LEGACY_RANGES,
    WIDE_RANGES,
    RandomisationRanges,
    sample_params,
    simulate_session,
)

# C8 §4/T4: ~20k sessions, a ~10× increase on Polito's 1,976 welds. The number
# is a default, not a constant of nature — tests pass a much smaller one.
DEFAULT_N_SESSIONS = 20_000

CORPUS_DIR = Path(__file__).resolve().parent.parent / "experiments" / "corpora"


@dataclass(frozen=True)
class CorpusSpec:
    """Everything needed to regenerate a corpus bit-for-bit.

    `seed` is the base seed: session i is simulated from `seed + i`. `ranges`
    is the distribution sample_params draws from — recorded here rather than
    assumed, which is the whole point of C8/D1 (a corpus must be able to say
    which distribution produced it).
    """

    name: str
    seed: int = SEED
    n_sessions: int = DEFAULT_N_SESSIONS
    n_frames: int = 1500
    ranges: RandomisationRanges = LEGACY_RANGES

    def as_dict(self) -> dict:
        """JSON-ready manifest form (ranges nested as their own dict)."""
        return {
            "name": self.name,
            "seed": self.seed,
            "n_sessions": self.n_sessions,
            "n_frames": self.n_frames,
            "ranges": self.ranges.as_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CorpusSpec":
        """Inverse of as_dict(): rebuild a spec from a persisted manifest."""
        return cls(
            name=d["name"],
            seed=int(d["seed"]),
            n_sessions=int(d["n_sessions"]),
            n_frames=int(d["n_frames"]),
            ranges=RandomisationRanges.from_dict(d["ranges"]),
        )

    def fingerprint(self) -> str:
        """Short stable hash of the manifest — the corpus's identity in runs.csv.

        Two corpora share a fingerprint if and only if they would generate the
        same sessions, so a run that records the fingerprint records exactly
        which data it saw.
        """
        blob = json.dumps(self.as_dict(), sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:12]

    def session_id(self, i: int) -> str:
        return f"{self.name}_{i:06d}"

    def session_seed(self, i: int) -> int:
        return self.seed + i


# The T3 pair: identical in every field except `ranges`.
GOLDAK_WIDE = CorpusSpec(name="goldak-wide", ranges=WIDE_RANGES)
GOLDAK_NARROW = CorpusSpec(name="goldak-narrow", ranges=LEGACY_RANGES)

CORPUS_VARIANTS = {"wide": GOLDAK_WIDE, "narrow": GOLDAK_NARROW}


def resolve_spec(variant: str = "wide", n_sessions: int | None = None,
                 seed: int | None = None, n_frames: int | None = None) -> CorpusSpec:
    """Look up a predefined variant and override its size/seed for a run.

    The corpus SIZE is a parameter precisely so tests (and smoke runs) can ask
    for 12 sessions instead of 20,000; overriding it produces a different
    fingerprint, which is correct — a 12-session corpus is not the 20k one.
    """
    if variant not in CORPUS_VARIANTS:
        raise ValueError(f"unknown corpus variant {variant!r}; "
                         f"known: {sorted(CORPUS_VARIANTS)}")
    base = CORPUS_VARIANTS[variant]
    return CorpusSpec(
        name=base.name,
        seed=base.seed if seed is None else seed,
        n_sessions=base.n_sessions if n_sessions is None else n_sessions,
        n_frames=base.n_frames if n_frames is None else n_frames,
        ranges=base.ranges,
    )


def generate_corpus(spec: CorpusSpec) -> list[SessionTensor]:
    """Simulate every session in `spec`, in order. Deterministic from the spec."""
    sessions = []
    for i in range(spec.n_sessions):
        params = sample_params(spec.session_seed(i), spec.session_id(i),
                               ranges=spec.ranges)
        params.n_frames = spec.n_frames
        session = simulate_session(params)
        session.meta["corpus"] = spec.name
        sessions.append(session)
    return sessions


def load_goldak_sessions(variant: str = "wide", n_sessions: int | None = None,
                         seed: int | None = None,
                         n_frames: int | None = None) -> tuple[list[SessionTensor], CorpusSpec]:
    """Convenience for CLIs: (sessions, spec) for a named variant.

    Returns the spec alongside the data so the caller can record the
    fingerprint and the ranges in its run config without rebuilding them.
    """
    spec = resolve_spec(variant, n_sessions=n_sessions, seed=seed, n_frames=n_frames)
    return generate_corpus(spec), spec


# ------------------------------------------------------------- persistence

def manifest_path(spec: CorpusSpec, corpus_dir: Path = CORPUS_DIR) -> Path:
    """Where a spec's manifest lives: one file per (name, fingerprint) pair."""
    return Path(corpus_dir) / f"{spec.name}_{spec.fingerprint()}.json"


def save_corpus_manifest(spec: CorpusSpec, corpus_dir: Path = CORPUS_DIR) -> Path:
    """Persist seed + ranges + size as JSON. The arrays are NOT persisted —
    they regenerate from this file exactly (see module docstring)."""
    path = manifest_path(spec, corpus_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(spec.as_dict(), indent=2, sort_keys=True) + "\n")
    return path


def load_corpus_manifest(path: Path) -> CorpusSpec:
    """Read a persisted manifest back into a CorpusSpec."""
    return CorpusSpec.from_dict(json.loads(Path(path).read_text()))


# ----------------------------------------------------------- OOD reservation

def thickness_ood_predicate(lo: float, hi: float):
    """Reserve plate-thickness extremes for the "ood" split (splits.py, D9).

    Returns a meta-predicate for split_sessions: sessions whose simulated
    plate thickness falls outside [lo, hi] never enter train/val/test. Not
    applied by default — C8's corpus questions are about coverage, and
    carving out the extremes would narrow the very axis D1 widened — but the
    hook exists so a generalisation test can be run without regenerating.
    """
    def predicate(meta: dict) -> bool:
        thickness = meta.get("params", {}).get("plate_thickness_mm")
        return thickness is not None and not (lo <= thickness <= hi)

    return predicate
