
The implementation plan is saved at `.cursor/plans/metal-heatmap-y-position-clipping-fix-plan.md`. Summary:

## Plan Summary

### Approach
- Lower workpiece base Y from **-0.6 → -0.85** so metal surface max stays below the weld pool.
- Keep `uMaxDisplacement` at 0.5 (avoid affecting HeatmapPlate3D).
- Introduce `welding3d.ts` constants and use them in TorchWithHeatmap3D.

### Phases (3)

| Phase | Goal | Steps | Time |
|-------|------|-------|------|
| **1. Foundation** | Constants and single source of truth | 3 | ~0.5 h |
| **2. Core Fix** | TorchWithHeatmap3D position updates | 6 | ~0.65 h |
| **3. Verification** | Tests, manual checks, docs | 7 | ~0.8 h |

**Total:** ~2.5–3 h (including buffer)

### Steps (16 total)

1. Add `welding3d.ts` with `WORKPIECE_BASE_Y`, `WELD_POOL_CENTER_Y`, `ANGLE_RING_Y`, etc.
2. Add unit test that enforces `metal_surface_max_Y < weld_pool_center_Y`.
3. Update TorchWithHeatmap3D: workpiece group, angle ring, grid, ContactShadows.
4. Manual checks on replay and demo pages.
5. Update ThermalPlate JSDoc and optional CONTEXT.md.

### Critical design

- `WORKPIECE_BASE_Y = -0.85` → metal max Y = -0.35, gap vs weld pool ≈ 0.15.
- Angle ring, grid, and ContactShadows derived from `WORKPIECE_BASE_Y`.
- Failure modes and fixes documented (e.g., if still clipping → try -0.9).

### What’s included

- Pre-planning analysis (synthesis, dependencies, risks).
- Step classification (critical vs non‑critical).
- Verification tests with setup, actions, pass criteria.
- Failure/success handling per step.
- Pre-flight checklist per phase.
- Risk overview and top risks.
- 12 success criteria (P0/P1).
- Progress tracking table.
- 3 thinking checkpoints and implementability notes.

Implementation can start with Phase 1, Step 1.1 (create `welding3d.ts`).
