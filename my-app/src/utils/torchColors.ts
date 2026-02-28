/**
 * Torch and weld pool color utilities.
 *
 * Shared between TorchViz3D (HUD temp readout) and TorchSceneContent (arc sphere,
 * arc under-light). Single source of truth for thermal color mapping.
 * Matches heatmapFragment.glsl anchor colors (green → orange → red).
 *
 * @see docs/ISSUE_THERMAL_GRADIENT_GREEN_ORANGE_RED.md
 * @see docs/ISSUE_TORCH_VIZ3D_VISUAL_LEGITIMACY.md
 */

import * as THREE from 'three';

/**
 * Arc / weld pool color: cold green → orange → red. IR-style thermal.
 * Thresholds: <200°C cold→mid, <400°C mid→hot, ≥400°C hot→hotEnd.
 */
export function getArcColor(temp: number): THREE.Color {
  const cold = new THREE.Color(0x22c55e);
  const mid = new THREE.Color(0xf97316);
  const hot = new THREE.Color(0xef4444);
  const hotEnd = new THREE.Color(0xfa0505);
  if (temp < 200) return new THREE.Color().lerpColors(cold, mid, temp / 200);
  if (temp < 400) return new THREE.Color().lerpColors(mid, hot, (temp - 200) / 200);
  return new THREE.Color().lerpColors(hot, hotEnd, Math.min((temp - 400) / 150, 1));
}

/**
 * HUD temp readout Tailwind class: green <250°C, amber 250–500°C, red >500°C.
 */
export function getTempReadoutColor(temp: number): string {
  if (temp < 250) return 'text-green-500';
  if (temp < 500) return 'text-amber-500';
  return 'text-red-500';
}
