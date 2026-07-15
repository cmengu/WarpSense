"""
c6_collapse_ablations.py — the C6 study driver (issue #14, spec #18).

One knob at a time from the C4 default config (window=300, stride=50,
n_blocks=4, ratio 0.40-0.50, EMA 0.996, seed 1337), 1 seed for the sweep:

  knob 2 (collapse check):      sharedweights (--ema-decay 0.0)
  knob 3 (window length):       w600, w1000            (+ default = w300)

Each config is a real `python -m world_model.pretraining.jepa` run (its own
process, so seeds/runs.csv behave exactly as a hand-launched run). Logs land
in notebook/logs/c6_<name>.log; the manifest (config -> checkpoint -> wall
time) in notebook/c6_manifest.csv. Afterwards every checkpoint is scored by
the C5 ruler on --split val:

  python -m world_model.eval.compare_pretrains <manifest checkpoints> --split val

Run from backend/:  venv/bin/python world_model/experiments/notebook/c6_collapse_ablations.py
Parallelism: N_WORKERS processes, OMP_NUM_THREADS split across them (M2: 2x4).
"""

import csv
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]   # .../backend
NOTEBOOK = Path(__file__).resolve().parent
LOGS = NOTEBOOK / "logs"
MANIFEST = NOTEBOOK / "c6_manifest_essential.csv"

PYTHON = str(BACKEND / "venv" / "bin" / "python")
N_WORKERS = 2
THREADS_PER_WORKER = "4"

# name -> extra CLI args on top of the C4 default (the first row IS the default)
CONFIGS: list[tuple[str, list[str]]] = [
    ("sharedweights", ["--ema-decay", "0.0"]),
    ("w600",          ["--window", "600"]),
    ("w1000",         ["--window", "1000"]),
]


def run_config(name: str, extra: list[str]) -> dict:
    log_path = LOGS / f"c6_{name}.log"
    cmd = [PYTHON, "-m", "world_model.pretraining.jepa", *extra]
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
    final = re.search(r"TEST latent MSE .*", text)
    row = {
        "name": name,
        "args": " ".join(extra),
        "returncode": proc.returncode,
        "wall_min": round(wall / 60, 1),
        "checkpoint": Path(ckpt.group(1)).name if ckpt else "",
        "final": final.group(0) if final else "(missing)",
    }
    print(f"[{name}] exit={proc.returncode} {row['wall_min']}min "
          f"{row['checkpoint']} :: {row['final']}", flush=True)
    return row


def main() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    print(f"C6 sweep: {len(CONFIGS)} configs, {N_WORKERS} workers "
          f"x OMP_NUM_THREADS={THREADS_PER_WORKER}", flush=True)
    with ThreadPoolExecutor(max_workers=N_WORKERS) as pool:
        rows = list(pool.map(lambda c: run_config(*c), CONFIGS))

    with open(MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"manifest: {MANIFEST}", flush=True)

    failed = [r["name"] for r in rows if r["returncode"] != 0 or not r["checkpoint"]]
    if failed:
        print(f"FAILED configs: {failed}", flush=True)
        sys.exit(1)
    ckpts = " ".join(f"experiments/checkpoints/{r['checkpoint']}" for r in rows)
    print("score with the C5 ruler (from backend/):\n"
          f"  venv/bin/python -m world_model.eval.compare_pretrains {ckpts} --split val",
          flush=True)


if __name__ == "__main__":
    main()
