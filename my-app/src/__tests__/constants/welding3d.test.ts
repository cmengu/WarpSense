/**
 * Tests for welding3d.ts — ensures metal surface stays below weld pool.
 *
 * Constraint: metal_surface_max_Y < weld_pool_center_Y
 * metal_surface_max_Y = WORKPIECE_BASE_Y + MAX_THERMAL_DISPLACEMENT
 *
 * @see .cursor/issues/metal-heatmap-y-position-clipping-torch.md
 */

import {
  WORKPIECE_BASE_Y,
  MAX_THERMAL_DISPLACEMENT,
  WELD_POOL_CENTER_Y,
  METAL_TO_TORCH_GAP,
} from '@/constants/welding3d';

describe('welding3d constants', () => {
  it('metal surface max stays below weld pool center (no clipping)', () => {
    const metal_surface_max_Y = WORKPIECE_BASE_Y + MAX_THERMAL_DISPLACEMENT;
    expect(metal_surface_max_Y).toBeLessThan(WELD_POOL_CENTER_Y);
  });

  it('gap between metal max and weld pool is at least 0.1 (safety margin)', () => {
    const metal_surface_max_Y = WORKPIECE_BASE_Y + MAX_THERMAL_DISPLACEMENT;
    const gap = WELD_POOL_CENTER_Y - metal_surface_max_Y;
    expect(gap).toBeGreaterThanOrEqual(0.1);
  });

  it('METAL_TO_TORCH_GAP matches derived gap', () => {
    const metal_surface_max_Y = WORKPIECE_BASE_Y + MAX_THERMAL_DISPLACEMENT;
    const gap = WELD_POOL_CENTER_Y - metal_surface_max_Y;
    expect(gap).toBe(METAL_TO_TORCH_GAP);
  });
});
