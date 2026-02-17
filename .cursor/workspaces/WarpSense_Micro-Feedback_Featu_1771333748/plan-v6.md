
The refined plan is complete. Summary of the main updates:

## Refined Plan Summary

Refinements applied from the critique:

### Phase 1 — Types & Micro-Feedback Library

1. **MicroFeedbackItem: required `frameIndex` and `type`** — Optionality removed so click-to-scrub is always valid.
2. **Severity exhaustivity** — Added grep-based checks and handling for `info`, `warning`, and `critical`.
3. **generateMicroFeedback robustness** — Input validation, null/NaN guards for angle and thermal, and an outer try-catch that returns `[]` on error.
4. **Thermal generator** — Explicit guards for `null`/`undefined`/`NaN` on north, south, east, west.
5. **Tests** — Required cases: empty arrays, 10k frames, angle-only, thermal-only, null sensors, NaN angles.

### Phase 2 — FeedbackPanel

1. **Severity styling** — Uses a `SEVERITY_STYLES` constant instead of hardcoded classes.
2. **onFrameSelect handling** — Always guarded; never called without a `typeof` check.
3. **frameIndex validation** — Ensures `frameIndex` is a number, in range, and bounds are checked before `frames[frameIndex]`.
4. **Keys** — Uses `fb-${frameIndex}-${type}` for micro and `session-${severity}-${i}` for session items to avoid collisions.

### Phase 3 — Replay Integration

1. **useMemo** — Dependencies documented; guards against recomputing on every frame tick.
2. **try-catch** — `generateMicroFeedback` is wrapped in try-catch inside `useMemo`.
3. **Timeline markers** — Handles single-frame and identical timestamps; hides markers when `duration <= 0` to avoid division by zero.
4. **frames prop** — Uses `frames={sessionData?.frames ?? []}` so FeedbackPanel always receives an array.
5. **SSR / hydration** — New Step 3.9 to verify Replay is client-only and no hydration mismatch occurs.
6. **Edge cases** — Empty session, single frame, missing sensor data, and loading state all handled explicitly.

### Cross-cutting changes

- **Red Team** — Added mitigations for optional props, key collisions, and SSR.
- **Implementability test** — Added Q&A for `onFrameSelect` undefined and single-frame sessions.
- **Progress tracking** — Updated for 28 total steps (14 in Phase 3 including the SSR step).
