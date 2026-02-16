/**
 * Tests for thermalInterpolation.ts — 5-point IDW interpolation for 3D heatmap.
 *
 * @see .cursor/plans/3d-warped-heatmap-plate-implementation-plan.md Step 1.2
 */

import {
  sanitizeTemp,
  interpolateThermalGrid,
} from "@/utils/thermalInterpolation";

describe("sanitizeTemp", () => {
  it("returns value for finite numbers", () => {
    expect(sanitizeTemp(100)).toBe(100);
    expect(sanitizeTemp(0)).toBe(0);
    expect(sanitizeTemp(600)).toBe(600);
  });

  it("clamps to [0, 600]", () => {
    expect(sanitizeTemp(-10)).toBe(0);
    expect(sanitizeTemp(700)).toBe(600);
  });

  it("replaces NaN with 20", () => {
    expect(sanitizeTemp(NaN)).toBe(20);
  });

  it("replaces Infinity with 20", () => {
    expect(sanitizeTemp(Infinity)).toBe(20);
    expect(sanitizeTemp(-Infinity)).toBe(20);
  });
});

describe("interpolateThermalGrid", () => {
  it("center value dominates at (0.5, 0.5) — grid[5][5] ≈ 100 for 10×10", () => {
    const grid = interpolateThermalGrid(100, 50, 50, 80, 80, 10);
    expect(grid[5][5]).toBeCloseTo(100, 0);
  });

  it("north edge: grid[0][5] ≈ 50 for 10×10", () => {
    const grid = interpolateThermalGrid(100, 50, 50, 80, 80, 10);
    expect(grid[0][5]).toBeCloseTo(50, 0);
  });

  it("south edge: grid[9][5] ≈ 50 for 10×10", () => {
    const grid = interpolateThermalGrid(100, 50, 50, 80, 80, 10);
    expect(grid[9][5]).toBeCloseTo(50, 0);
  });

  it("east edge: grid[5][9] ≈ 80 for 10×10", () => {
    const grid = interpolateThermalGrid(100, 50, 50, 80, 80, 10);
    expect(grid[5][9]).toBeCloseTo(80, 0);
  });

  it("west edge: grid[5][0] ≈ 80 for 10×10", () => {
    const grid = interpolateThermalGrid(100, 50, 50, 80, 80, 10);
    expect(grid[5][0]).toBeCloseTo(80, 0);
  });

  it("all same temp yields uniform grid", () => {
    const grid = interpolateThermalGrid(200, 200, 200, 200, 200, 10);
    for (let y = 0; y < 10; y++) {
      for (let x = 0; x < 10; x++) {
        expect(grid[y][x]).toBe(200);
      }
    }
  });

  it("respects gridSize parameter (50×50)", () => {
    const grid = interpolateThermalGrid(100, 50, 50, 80, 80, 50);
    expect(grid).toHaveLength(50);
    expect(grid[0]).toHaveLength(50);
    expect(grid[25][25]).toBeCloseTo(100, 0);
  });

  it("returns no NaN in output", () => {
    const grid = interpolateThermalGrid(100, 50, 50, 80, 80, 20);
    for (const row of grid) {
      for (const v of row) {
        expect(Number.isNaN(v)).toBe(false);
      }
    }
  });

  it("returns finite values for NaN input", () => {
    const grid = interpolateThermalGrid(NaN, 50, 50, 80, 80, 10);
    for (const row of grid) {
      for (const v of row) {
        expect(Number.isFinite(v)).toBe(true);
      }
    }
  });

  it("returns finite values for Infinity input", () => {
    const grid = interpolateThermalGrid(100, Infinity, 50, 80, 80, 10);
    for (const row of grid) {
      for (const v of row) {
        expect(Number.isFinite(v)).toBe(true);
      }
    }
  });

  it("clamps negative input to 0", () => {
    const grid = interpolateThermalGrid(-100, -100, -100, -100, -100, 5);
    for (const row of grid) {
      for (const v of row) {
        expect(v).toBeGreaterThanOrEqual(0);
      }
    }
  });

  it("default gridSize is 100", () => {
    const grid = interpolateThermalGrid(100, 100, 100, 100, 100);
    expect(grid).toHaveLength(100);
    expect(grid[0]).toHaveLength(100);
  });
});
