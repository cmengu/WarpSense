/**
 * Unit tests for heatmap shader utils — temperature→color mapping.
 *
 * Verifies 5–10°C produces visibly different colors per unified-torch-heatmap-replay-plan.
 *
 * @see my-app/src/utils/heatmapShaderUtils.ts
 * @see .cursor/plans/unified-torch-heatmap-replay-plan.md Step 1.1
 */

import { temperatureToColor } from '@/utils/heatmapShaderUtils';

function rgbDiff(
  a: [number, number, number],
  b: [number, number, number]
): number {
  return Math.max(
    Math.abs(a[0] - b[0]),
    Math.abs(a[1] - b[1]),
    Math.abs(a[2] - b[2])
  );
}

describe('temperatureToColor', () => {
  it('produces visibly different colors for 10°C difference (100 vs 110)', () => {
    const c100 = temperatureToColor(0, 500, 10, 100);
    const c110 = temperatureToColor(0, 500, 10, 110);
    const diff = rgbDiff(c100, c110);
    expect(diff).toBeGreaterThan(0.06);
  });

  it('produces different colors for 5°C difference (100 vs 105)', () => {
    const c100 = temperatureToColor(0, 500, 5, 100);
    const c105 = temperatureToColor(0, 500, 5, 105);
    const diff = rgbDiff(c100, c105);
    expect(diff).toBeGreaterThan(0.01);
  });

  it('returns cool blue at 0°C', () => {
    const [r, g, b] = temperatureToColor(0, 500, 10, 0);
    expect(r).toBeCloseTo(0.12, 2);
    expect(g).toBeCloseTo(0.23, 2);
    expect(b).toBeGreaterThan(0.5);
  });

  it('returns purple at 500°C', () => {
    const [r, g, b] = temperatureToColor(0, 500, 10, 500);
    expect(r).toBeCloseTo(0.66, 2);
    expect(g).toBeCloseTo(0.33, 2);
    expect(b).toBeGreaterThan(0.9);
  });

  it('clamps temperatures above maxTemp', () => {
    const c500 = temperatureToColor(0, 500, 10, 500);
    const c600 = temperatureToColor(0, 500, 10, 600);
    expect(c500).toEqual(c600);
  });

  it('clamps temperatures below minTemp', () => {
    const c0 = temperatureToColor(0, 500, 10, 0);
    const cNeg = temperatureToColor(0, 500, 10, -50);
    expect(c0).toEqual(cNeg);
  });

  it('avoids div-by-zero when maxTemp equals minTemp', () => {
    const c = temperatureToColor(100, 100, 10, 100);
    expect(c.every((v) => Number.isFinite(v))).toBe(true);
  });
});
