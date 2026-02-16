/**
 * WebGL context limits and usage guidance.
 *
 * Browsers limit ~8–16 WebGL contexts per tab. Each Canvas creates one.
 * Replay/Demo use 2 TorchWithHeatmap3D = 2 Canvases. HeatmapPlate3D deprecated
 * in replay (thermal now on metal in TorchWithHeatmap3D).
 *
 * @see documentation/WEBGL_CONTEXT_LOSS.md
 * @see .cursor/issues/webgl-context-lost-consistent-project-wide.md
 */

/**
 * Maximum 3D Canvas instances per page (TorchViz3D or TorchWithHeatmap3D).
 * Exceeding risks WebGL context loss. Demo and replay use 2 TorchWithHeatmap3D.
 *
 * @see my-app/eslint-rules/max-torchviz3d-per-page.cjs — ESLint enforces this
 */
export const MAX_TORCHVIZ3D_PER_PAGE = 2;

/**
 * Maximum total Canvas instances per page.
 * Replay/Demo: 2 TorchWithHeatmap3D = 2 Canvases. HeatmapPlate3D deprecated in replay.
 *
 * @see TorchWithHeatmap3D in components/welding/TorchWithHeatmap3D.tsx
 */
export const MAX_CANVAS_PER_PAGE = 2;
