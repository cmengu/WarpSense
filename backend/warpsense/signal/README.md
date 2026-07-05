# signal/ — signal truth

**Role:** physical facts about the sensor stream. Arc state, null-safe
statistics, thermal geometry, window sizes. One line each in the module
docstrings; start there.

**Inputs:** frames (pydantic `Frame`, dicts, or DataFrames — each helper
documents which shape it takes). **Outputs:** floats, bools, masks.

**Imported by:** `features/` (all three extractors), `floor/`,
`classifier/` (via its feature extractor). **Imports:** only `contracts/`
and third-party libs — never `features/`, `floor/`, `classifier/`,
`agents/`, or `api/`.

**Invariant — no judgments here.** Nothing in this package encodes what a
*good* weld is: no quality thresholds, no scores, no labels. `arc_on`'s
5 V / 5 A floor is a physical noise floor, not a quality bar. If a change
here makes a weld pass or fail differently, that change belongs one layer
up — and the snapshot suite (`tests/snapshots/`) will show exactly which
downstream numbers moved.

**Deliberate exclusions:** `realtime/` keeps its own latency-tuned
thresholds and does not import this package. `usable_for()` from the
original design sketch is omitted until it has a real consumer.
