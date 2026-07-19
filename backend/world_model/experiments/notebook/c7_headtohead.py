"""
c7_headtohead.py — the C7 decisive-comparison driver (issue #15, spec #18).

Trains the five checkpoints C7 still needs, then scores the contenders on
--split test — the single pre-registered touch of the test split.

SCORING DESIGN (revised mid-run, before any test-split look): `--seed` is
salted into the split hash (data/splits.py), so seeds 1338/1339 train on a
DIFFERENT train/test partition than 1337. Scoring all six on the seed-1337
test split would be asymmetric — the 1338/1339 encoders pretrained on most
of those welds (unlabeled, but still a leak the 1337 models don't get).
Fix, using existing code only: score SEED-MATCHED PAIRS — for each seed s,
one `compare_pretrains --seed s --split test` call scoring that seed's JEPA
+ masked recon + random floor on the test split neither encoder trained on.
The verdict metric is the paired JEPA-minus-masked-recon difference across
the 3 seeds ("beyond seed noise", tie -> incumbent). Still one verdict pass.

Contenders (3 seeds each, identical diet: window=300, stride=50, 30 epochs,
full Polito data):

  JEPA default config (C6 winner on val):
    seed 1337 -> already trained in C6 (jepa_pretrain_e7f0e92d7625.pt)
    seed 1338, seed 1339 -> trained here
  masked recon --window 300 (the incumbent/control):
    seed 1337, 1338, 1339 -> trained here (only a tiny-preset ckpt existed)

Tie rule (pre-registered): incumbent wins — masked recon keeps the Step 9+
warm-start slot unless JEPA clearly beats it beyond seed noise.

Run from backend/:
  venv/bin/python world_model/experiments/notebook/c7_headtohead.py
Logs land in notebook/logs/c7_<name>.log; manifest in notebook/c7_manifest.csv.
Parallelism: 2 worker processes x OMP_NUM_THREADS=4 (same as C6).
"""

import csv
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]   # .../backend
NOTEBOOK = Path(__file__).resolve().parent
LOGS = NOTEBOOK / "logs"
MANIFEST = NOTEBOOK / "c7_manifest.csv"
CHECKPOINTS = NOTEBOOK.parent / "checkpoints"

PYTHON = str(BACKEND / "venv" / "bin" / "python")
N_WORKERS = 2
THREADS_PER_WORKER = "4"

# C6's default-config seed-1337 checkpoint, reused as JEPA entrant seed 1.
JEPA_1337 = CHECKPOINTS / "jepa_pretrain_e7f0e92d7625.pt"

# name -> (module, extra CLI args). Every run is full data, 30 epochs.
RUNS: list[tuple[str, str, list[str]]] = [
    ("jepa_s1338", "world_model.pretraining.jepa",        ["--seed", "1338"]),
    ("jepa_s1339", "world_model.pretraining.jepa",        ["--seed", "1339"]),
    ("mr_s1337",   "world_model.pretraining.masked_recon", ["--window", "300", "--seed", "1337"]),
    ("mr_s1338",   "world_model.pretraining.masked_recon", ["--window", "300", "--seed", "1338"]),
    ("mr_s1339",   "world_model.pretraining.masked_recon", ["--window", "300", "--seed", "1339"]),
]


def run_one(name: str, module: str, extra: list[str]) -> dict:
    log_path = LOGS / f"c7_{name}.log"
    cmd = [PYTHON, "-m", module, *extra]
    env = {**os.environ, "OMP_NUM_THREADS": THREADS_PER_WORKER}
    t0 = time.monotonic()
    with open(log_path, "w") as log:
        log.write(f"$ {' '.join(cmd)}\n")
        log.flush()
        proc = subprocess.run(cmd, cwd=BACKEND, env=env,
                              stdout=log, stderr=subprocess.STDOUT)
    wall = time.monotonic() - t0
    text = log_path.read_text()
    ckpt = re.search(r"transfer artifact: (\S+)", text)
    final = text.strip().splitlines()[-1] if text.strip() else ""
    return {
        "name": name,
        "args": " ".join(extra),
        "returncode": proc.returncode,
        "wall_min": round(wall / 60, 1),
        "checkpoint": Path(ckpt.group(1)).name if ckpt else "",
        "final": final,
    }


def main() -> None:
    LOGS.mkdir(exist_ok=True)
    print(f"C7: {len(RUNS)} training runs, {N_WORKERS} workers")
    with ThreadPoolExecutor(max_workers=N_WORKERS) as pool:
        rows = list(pool.map(lambda r: run_one(*r), RUNS))

    with open(MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r)

    failed = [r for r in rows if r["returncode"] != 0 or not r["checkpoint"]]
    if failed:
        print(f"ABORT before test-split scoring — {len(failed)} run(s) failed: "
              f"{[r['name'] for r in failed]}")
        raise SystemExit(1)

    # The single pre-registered touch of --split test, seed-matched pairs
    # (see SCORING DESIGN in the module docstring).
    by_name = {r["name"]: r["checkpoint"] for r in rows}
    pairs = {
        "1337": [str(JEPA_1337), str(CHECKPOINTS / by_name["mr_s1337"])],
        "1338": [str(CHECKPOINTS / by_name["jepa_s1338"]),
                 str(CHECKPOINTS / by_name["mr_s1338"])],
        "1339": [str(CHECKPOINTS / by_name["jepa_s1339"]),
                 str(CHECKPOINTS / by_name["mr_s1339"])],
    }
    rc = 0
    for seed, ckpts in pairs.items():
        cmd = [PYTHON, "-m", "world_model.eval.compare_pretrains",
               *ckpts, "--split", "test", "--seed", seed]
        print(f"\n$ {' '.join(cmd)}")
        score_log = LOGS / f"c7_test_scoring_s{seed}.log"
        with open(score_log, "w") as log:
            log.write(f"$ {' '.join(cmd)}\n")
            log.flush()
            proc = subprocess.run(cmd, cwd=BACKEND, env={**os.environ},
                                  stdout=log, stderr=subprocess.STDOUT)
        print(score_log.read_text())
        rc = rc or proc.returncode
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
