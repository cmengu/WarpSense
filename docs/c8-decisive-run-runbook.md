# C8 decisive run — execution runbook

How to actually execute `backend/world_model/experiments/notebook/c8_headtohead.py`
on a GPU box. The driver is fully written and stub-tested (`tests/test_c8_driver.py`,
28 tests); this document is only about *running* it. Written 2026-07-19, against
PR #29 (`feat/c8-implementation`).

## What the run spends

- **Training:** 15 new checkpoints — 3 seeds (1337/1338/1339) × 5 arms
  (JEPA·goldak-wide, masked-recon·{goldak-wide, goldak-narrow, spectrum-random},
  supervised-depth·goldak-wide), 30 epochs each over a 20,000-session simulated
  corpus (`N_SESSIONS`/`CORPUS_SEED` in the driver). The driver runs 2 training
  subprocesses at a time (`N_WORKERS = 2` — one per GPU on a 2×A100 box works out
  naturally, but note the subprocesses do NOT pin devices; see step 4).
- **Scoring:** 21 checkpoints (15 new + C7's six Polito incumbents, reused from
  the repo — they are committed under `backend/world_model/experiments/checkpoints/`,
  ~1.6 MB, so a clone carries them) through the `--dual-eval --split test` pass.
- **Corpus generation:** the goldak-wide / goldak-narrow / spectrum-random corpora
  are generated on the fly at `CORPUS_SEED`, identically for every arm, and their
  manifests written to `experiments/corpora/` (gitignored, regenerable bit-for-bit).

## Steps

```bash
# 1. clone + branch
git clone https://github.com/cmengu/WarpSense.git && cd WarpSense
git checkout feat/c8-implementation          # or main, after PR #29 merges

# 2. env — the driver invokes backend/venv/bin/python by absolute path,
#    so the venv MUST live at backend/venv
cd backend
python3 -m venv venv
venv/bin/pip install -r requirements.txt     # torch build: see GPU note below
# sanity: the whole C8 surface
venv/bin/python -m pytest tests/test_c8_*.py -q        # expect 201 passed

# 3. REHEARSAL on CPU at toy scale (~15 min): executes the ENTIRE driver —
#    train, Gate C8-0, scoring, seed pooling, adjudication, ledger — with toy
#    corpora, 2 seeds, and scoring on --split val, so the one pre-registered
#    test-split touch is NOT spent. Every output is stamped REHEARSAL.
#    Expect a complete 9-row §7 ledger (no "not-run" rows) at the end; then
#    delete the rehearsal checkpoints/logs it leaves (all regenerable).
C8_REHEARSAL=1 venv/bin/python -m world_model.experiments.notebook.c8_headtohead

# 4. the decisive run
export C8_DEVICE=cuda      # every training/scoring subprocess inherits this
nohup venv/bin/python -m world_model.experiments.notebook.c8_headtohead \
    > c8_run.log 2>&1 &
tail -f c8_run.log         # per-run logs: world_model/experiments/notebook/logs/c8_*.log
```

GPU note (Hummingbird 2×A100, driver 530): install a cu124/cu126 torch wheel —
cu128+ wheels will not load on driver 530. The subprocesses all see the same
`CUDA_VISIBLE_DEVICES`; with `N_WORKERS = 2` two trainings share GPU 0 unless you
either leave it (the models are small; sharing is fine) or split by editing
`run_one` to alternate `CUDA_VISIBLE_DEVICES` per worker.

## What the driver does, in order (do not reorder)

1. Trains the 15 checkpoints (2 workers), writes `c8_manifest.csv`; aborts if any
   run fails or any reused C7 checkpoint is missing (it never retrains them).
2. Runs **Gate C8-0 first** from Polito class counts alone and prints the TH1–TH5
   power table *before any decisive number exists*. Comparisons whose threshold
   sits below its MDE are BLOCKED — still scored for the record, but exploratory.
3. Touches `--split test` exactly once (guarded; a second look raises), scoring
   the seed-matched pairs through the dual-eval probe so ΔMAE(sim) and ΔAUC(real)
   come out paired.
4. Adjudicates TH1–TH5. A paired CI including zero yields exactly
   "underpowered — not decided" — the C7 tie-goes-to-incumbent sentence is
   unsayable by construction.

## Afterwards

- The driver now runs fully wired end to end: each scoring subprocess writes a
  paired-diff JSON (`--json-out`), the driver pools them across seeds (C7's
  mean-Δ convention with a combined CI), adjudicates TH1–TH5, and writes
  `c8_ledger.json` + `gate_status.md`. The ledger and gate table are the direct
  inputs to **#28** (the C8 verdict record) — no manual parsing remains.
- Commit `c8_manifest.csv`, the gate table, and the logs you want to keep on a
  results branch; corpora manifests regenerate and stay gitignored.
