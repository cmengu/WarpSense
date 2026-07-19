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
  supervised_depth.py — the one NON-self-supervised sibling: a linear head on
                    the same hidden states regresses the simulator's per-frame
                    fusion depth (C8 / trap T5, decision D4). It uses the depth
                    LABEL Goldak supplies for free, so it only runs on the
                    goldak corpus — but the encoder it trains is byte-for-byte
                    the same architecture as the SSL arms, so its checkpoint is
                    interchangeable with theirs. Objective is the ONLY variable.
"""
