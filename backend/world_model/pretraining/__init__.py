"""
pretraining/ — self-supervised objectives that teach the shared StemTrunkEncoder
(architecture/trunk.py) what weld dynamics look like, before any labelled training.

Every objective here is a sibling under one rule: it trains the shared encoder
and emits the SAME transfer checkpoint (common.py), so downstream warm-starts
(Step 7 encoder, Step 8 training) never care WHICH objective produced the
weights — swapping pretraining is a CLI argument, not a code change.

  masked_recon.py — hide scattered frames, reconstruct their raw sensor values
                    (the BERT recipe; Step 6 / Gate 0.5, formerly
                    training/pretrain_polito.py).
  jepa.py         — hide one contiguous block, predict its EMBEDDING (the
                    I-JEPA recipe). [C4 — not yet implemented]
"""
