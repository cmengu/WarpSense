
Refinements from the critique are applied. The updated plan is in `.cursor/plans/unified-torch-heatmap-implementation-blueprint.md`.

**Refinements made:**

1. **Step 2.1 (critical):** Added `if (readings.length === 0) return null;` after the readings assignment so behavior matches the unit test. The test expects `null` when `thermal_snapshots[0].readings` is empty.

2. **Step 2.2b:** Corrected SceneContent line reference from `lines ~63–130` to `lines ~64–189`.

3. **Step 4.1:** Clarified that it is a verification/audit step (grep to confirm no remnants). Steps 2.3 and 2.4 perform the removal.

4. **Step 1.5:** Unified pass criteria to: per-channel diff > 0.06 for at least one channel (R, G, or B).

5. **Step 2.2a:** Added a subtask to preserve the useEffect-for-DataTexture-update pattern during extraction to avoid GPU read races.

6. **Step 2.1:** Added a note to ensure `import type { ThermalDirection } from '@/types/thermal'` exists in `frameUtils.ts`.
