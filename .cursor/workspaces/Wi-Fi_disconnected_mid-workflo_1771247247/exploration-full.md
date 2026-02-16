
Verification from code review:

## Implementation verification

Implementation aligns with the plan. Here's what was checked:

### Phase 1: Foundation

| Item | Status |
|------|--------|
| `welding3d.ts` constants | All present (WORKPIECE_BASE_Y=-0.85, ANGLE_RING_Y, GRID_Y, CONTACT_SHADOWS_Y) |
| Math constraint | metal_max=-0.35 < weld_pool=-0.2, gap=0.15 |
| `welding3d.test.ts` | Constraint, gap ≥ 0.1, METAL_TO_TORCH_GAP tests |

### Phase 2: TorchWithHeatmap3D

| Item | Status |
|------|--------|
| Imports from welding3d | Imports WORKPIECE_BASE_Y, ANGLE_RING_Y, GRID_Y, CONTACT_SHADOWS_Y |
| WORKPIECE_GROUP_Y | `WORKPIECE_GROUP_Y = WORKPIECE_BASE_Y` exported |
| Workpiece group | `position={[0, WORKPIECE_GROUP_Y, 0]}` |
| Angle ring | `position={[0, ANGLE_RING_Y, 0]}` |
| Grid | `position={[0, GRID_Y, 0]}` |
| ContactShadows | `position={[0, CONTACT_SHADOWS_Y, 0]}` |
| No magic numbers | No -0.6/-0.59 in workpiece/ring/grid/shadows (torch internal -0.6 kept as planned) |

### Phase 3: Verification & docs

| Item | Status |
|------|--------|
| TorchWithHeatmap3D constants test | `WORKPIECE_GROUP_Y === WORKPIECE_BASE_Y` and `=== -0.85` |
| ThermalPlate JSDoc | References WORKPIECE_BASE_Y and welding3d |
| uMaxDisplacement comment | Links to MAX_THERMAL_DISPLACEMENT in welding3d.ts |

---

### Run verification tests

Run the automated tests:

```bash
cd my-app && npm test -- welding3d TorchWithHeatmap3D HeatmapPlate3D
```

Expected: all tests pass.

### Manual checks (per plan)

- Replay: open a session with thermal data, scrub to a hot frame (400°C+), rotate the view, confirm no metal clipping.
- Demo: open `/demo` with the expert session, same check.

---

Implementation is complete and consistent with the plan. The metal base is at Y = -0.85 (instead of -0.6), so the metal surface max with full displacement stays at about -0.35, below the weld pool at -0.2, with the intended 0.15 gap between metal and torch.
