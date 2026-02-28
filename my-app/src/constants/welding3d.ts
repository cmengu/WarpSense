/**
 * 3D welding scene Y-coordinate constants.
 *
 * Constraint: metal_surface_max_Y < weld_pool_center_Y (metal must stay below torch).
 * Metal surface max = WORKPIECE_BASE_Y + MAX_THERMAL_DISPLACEMENT (from ThermalPlate).
 *
 * @see .cursor/issues/metal-heatmap-y-position-clipping-torch.md
 */

/** Torch group base Y (world). Weld pool is below this. */
export const TORCH_GROUP_Y = 0.4;

/** Weld pool sphere Y relative to torch group. World Y = TORCH_GROUP_Y + WELD_POOL_OFFSET_Y. */
export const WELD_POOL_OFFSET_Y = -0.6;

/** Weld pool center world Y. Metal surface must stay below this. */
export const WELD_POOL_CENTER_Y = TORCH_GROUP_Y + WELD_POOL_OFFSET_Y; // -0.2

/** Max vertex displacement in ThermalPlate shader (uMaxDisplacement). Do not change without considering HeatmapPlate3D. */
export const MAX_THERMAL_DISPLACEMENT = 0.5;

/** Desired gap between metal max surface and weld pool center (world units). */
export const METAL_TO_TORCH_GAP = 0.02;

/** Workpiece base Y. Metal surface max = this + MAX_THERMAL_DISPLACEMENT. Must be < WELD_POOL_CENTER_Y - MAX_THERMAL_DISPLACEMENT. */
export const WORKPIECE_BASE_Y =
  WELD_POOL_CENTER_Y - MAX_THERMAL_DISPLACEMENT - METAL_TO_TORCH_GAP; // -0.85

/** Angle guide ring Y — slightly above metal surface (sits on workpiece). */
export const ANGLE_RING_Y = WORKPIECE_BASE_Y + 0.01;

/** Grid Y — aligns with workpiece base (metal plane). */
export const GRID_Y = WORKPIECE_BASE_Y;

/** ContactShadows Y — aligns with metal surface. */
export const CONTACT_SHADOWS_Y = WORKPIECE_BASE_Y + 0.01;
