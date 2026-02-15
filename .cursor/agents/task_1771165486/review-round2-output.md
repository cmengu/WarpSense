
Here’s a **code review** of the browser-only demo mode changes:

---

## Code review: browser-only demo mode

### 1. **`demo-data.ts`** — data generation

**Positives**
- Matches the plan: 15s, 10ms frames, thermal every 100ms.
- Thermal model: `base_temp`, `distance_factor`, `angle_offset` are documented.
- Deterministic: no randomness; easy to test and reason about.
- Expert vs novice behavior clearly separated (stable vs drifting).
- `disable_sensor_continuity_checks: true` for novice is appropriate for spikes.
- Thermal directions and distance order match the contract.

**Notes / suggestions**
1. **`_t_ms` unused**  
   `generateThermalSnapshot` takes `_t_ms` but doesn’t use it. Either remove it if time-based variation isn’t needed, or add time-based behavior if required later.

2. **Temperature magnitude**  
   For 150A × 22.5V: `base_temp ≈ 150 + 67.5 ≈ 217°C`. With `distance_factor` for 10mm ≈ 0.9, temps are ~200°C. That’s plausible for a simplified model; HeatMap’s scale is 20–600°C.

3. **Hardcoded scores**  
   Page shows 94/100 and 42/100. These are static, not computed from session data. Fine for a demo, but could be misleading if someone expects them to change. A short comment on the page would help.

---

### 2. **`demo/page.tsx`** — demo UI

**Positives**
- Clear separation of concerns: generation vs extraction vs components.
- `useState` with initializer keeps session generation on mount and stable.
- `useMemo` for heatmap/angle extraction avoids recomputation.
- Playback logic is clear: interval, stop at end, reset to 0.
- ErrorBoundary around WebGL and charts isolates failures.
- Dynamic import of `TorchViz3D` avoids SSR issues.
- `aria-label` and `role="status"` improve accessibility.
- “DEMO MODE — No backend required” clarifies context.

**Notes / suggestions**
1. **`DURATION_MS` / `FRAME_INTERVAL_MS` duplication**  
   Same constants appear in both `demo-data.ts` and `page.tsx`. Consider a single source (e.g. shared constants module) for consistency.

2. **Error handling in `useState` initializers**  
   You `throw` on error. If generation fails, the whole page crashes instead of showing an error UI. For a demo, showing a fallback message might be nicer. Optional improvement.

3. **Feedback text vs signal**  
   “Temperature spike at 2.3s” is illustrative; novice spikes occur at ~0.5s, 2.5s, etc. Consider aligning the copy with the model or making it more generic (“multiple temperature spikes”).

---

### 3. **`demo-data.test.ts`** — tests

**Positives**
- Exercises frame count, heatmap, and angle extraction.
- Ensures integration with `extractHeatmapData`, `extractAngleData`.
- Verifies thermal frame interval (every 100ms).
- Covers frame structure and metadata.

**Suggestions**
1. **Determinism**  
   `generateExpertSession()` uses `new Date().toISOString()` for `start_time` and `completed_at`, so those values change each run, but the tests don’t depend on them. That’s fine for determinism.

2. **Novice-specific behavior**  
   You could add tests for novice drift (e.g. angle 45°→65°, volts 22→18 over time) to lock in the intended behavior.

3. **Thermal snapshot structure**  
   A quick check that `thermal_snapshots` have all five directions and correct `distance_mm` ordering would strengthen the thermal contract.

---

### 4. **Alignment with project rules**

| Rule | Status |
|------|--------|
| Append-only | N/A (demo data is synthesized) |
| Single source of truth | Backend computes scoring; demo uses fixed scores |
| Exact replays | Uses `getFrameAtTimestamp` for deterministic replay |
| Type safety | Session/Frame/ThermalSnapshot used consistently |
| Validation | Tests cover shape and integration |
| Never silently fail | Errors are logged and rethrown |
| No randomness | Data generation is deterministic |

---

### 5. **Minor findings**

1. **Thermal snapshot ordering**  
   `DISTANCES_MM = [10, 20, 30, 40, 50]` is strictly increasing; `validateFrame` expects strictly increasing `distance_mm`. Correct.

2. **`heat_dissipation_rate_celsius_per_sec: null`**  
   All frames use `null`. The HeatMap uses `extractHeatmapData`, which doesn’t depend on dissipation; TorchViz3D uses `extractCenterTemperatureWithCarryForward`. So null dissipation is acceptable for the demo.

3. **`thermal_distance_interval_mm: 10`**  
   Matches `DISTANCES_MM` spacing and the spec.

---

### Verdict

The implementation matches the plan, keeps deterministic replay, follows the existing Session/Frame contracts, and integrates cleanly with the heatmap, angle graph, and 3D components. Tests cover the important paths and integration points. The minor suggestions above are optional polish; there are no blocking issues.
