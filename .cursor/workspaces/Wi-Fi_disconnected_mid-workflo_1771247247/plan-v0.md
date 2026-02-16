
Verification is blocked (commands keep getting rejected), so here’s the status from code review and how to verify manually.

---

## Implementation status: complete

The implementation matches the refined plan from `.cursor/plans/metal-heatmap-y-position-clipping-fix-plan.md`.

### Phase 1: Foundation

| Step | Status | Notes |
|------|--------|-------|
| 1.1 | Done | `welding3d.ts` exists with all constants; `WORKPIECE_BASE_Y = -0.85`, gap = 0.15 |
| 1.2 | Done | `welding3d.test.ts` checks metal_max < weld_pool, gap ≥ 0.1, `METAL_TO_TORCH_GAP` |
| 1.3 | N/A | Direct imports used; no barrel file |

### Phase 2: Core fix

| Step | Status | Notes |
|------|--------|------|
| 2.1 | Done | Imports `WORKPIECE_BASE_Y`, `ANGLE_RING_Y`, `GRID_Y`, `CONTACT_SHADOWS_Y` |
| 2.2 | Done | `WORKPIECE_GROUP_Y = WORKPIECE_BASE_Y` exported; workpiece group `[0, WORKPIECE_GROUP_Y, 0]` |
| 2.3–2.5 | Done | Angle ring, grid, `ContactShadows` use `ANGLE_RING_Y`, `GRID_Y`, `CONTACT_SHADOWS_Y` |
| 2.6 | Done | No magic `-0.6` / `-0.59` in workpiece/ring/grid/shadows; torch-internal `-0.6` is unchanged |

### Phase 3: Verification & docs

| Step | Status | Notes |
|------|--------|------|
| 3.2a | Done | `WORKPIECE_GROUP_Y === WORKPIECE_BASE_Y === -0.85` asserted in test |
| 3.5 | Done | ThermalPlate JSDoc references `WORKPIECE_BASE_Y`; `uMaxDisplacement` comment references `welding3d.ts` |

---

## Verification to run locally

Run automated tests:

```bash
cd my-app && npm test -- welding3d TorchWithHeatmap3D HeatmapPlate3D
```

Manual visual checks (per plan):

1. Replay page: open a session with thermal data, scrub to a hot frame (≥400°C), rotate 3D view, confirm no metal clipping.
2. Demo page: open `/demo` with expert session, same check.

---

## Summary

- Metal base: Y = -0.85 (was -0.6).
- Max metal surface: ≈ -0.35 (`-0.85 + 0.5`).
- Weld pool center: -0.2, so gap ≈ 0.15 between metal and torch.
- Single source of truth: `WORKPIECE_GROUP_Y = WORKPIECE_BASE_Y`.
- Tests: `welding3d.test.ts`, `TorchWithHeatmap3D.test.tsx`, and HeatmapPlate3D tests in place.

Implementation is done; run the test command above and the visual checks to confirm on your environment.
