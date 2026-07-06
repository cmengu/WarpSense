# Gate status (D11 — number vs threshold, or it didn't happen)

## Gate 1.5 — observability ceiling (2026-07-05)
- oracle ceiling MAE: **0.109 mm** (± 0.014 across 5 session-grouped folds) vs threshold 1.0 mm → **PASS**
- mean-predictor baseline: 0.660 mm; 1000 sessions / 29000 windows (w=100, stride=50), seed 1337
- caveat: pre-Gate-1 simulator — ceiling is provisional until calibration vs sectioned coupons (Step 9)

## Gate 0.5 — Polito pre-training (2026-07-06)
- kill criterion was "pipeline can't learn real electrical dynamics at all": held-out masked-recon MSE **0.00083** vs mean-predictor **0.0743** (~90× better) → **PASS**
- 1,976 real spot welds (1381/287/308 session split), 30 epochs, seed 1337, run 8a68998bf644
- transfer artifact: `checkpoints/polito_pretrain_8a68998bf644.pt` — {stems[volts], stems[amps], trunk}; heads excluded
- honest caveat: fault-bit head is weak (test macro-F1 0.14; recall 9/11 faults, 260 false positives from pos_weight=24) — expected under 79/1,897 imbalance, and the head does not transfer; recon is the objective that matters for warm-start

