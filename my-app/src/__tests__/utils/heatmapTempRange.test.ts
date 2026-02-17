/**
 * Tests for computeMinMaxTemp — heatmap temperature range fallback logic.
 *
 * Validates: empty array, null, undefined, invalid temp_celsius (NaN, Infinity),
 * mixed valid/invalid, and normal cases.
 */

import { computeMinMaxTemp } from "@/utils/heatmapTempRange";
import { THERMAL_MIN_TEMP, THERMAL_ABSOLUTE_MAX } from "@/constants/thermal";

describe("computeMinMaxTemp", () => {
  it("returns fallback when empty array", () => {
    const result = computeMinMaxTemp([]);
    expect(result).toEqual({ min: THERMAL_MIN_TEMP, max: THERMAL_ABSOLUTE_MAX });
  });

  it("returns fallback when null", () => {
    const result = computeMinMaxTemp(null);
    expect(result).toEqual({ min: THERMAL_MIN_TEMP, max: THERMAL_ABSOLUTE_MAX });
  });

  it("returns fallback when undefined", () => {
    const result = computeMinMaxTemp(undefined);
    expect(result).toEqual({ min: THERMAL_MIN_TEMP, max: THERMAL_ABSOLUTE_MAX });
  });

  it("returns correct min/max for valid points", () => {
    const result = computeMinMaxTemp([
      { temp_celsius: 100 },
      { temp_celsius: 400 },
    ]);
    expect(result).toEqual({ min: 100, max: 400 });
  });

  it("filters NaN and returns valid range from remaining", () => {
    const result = computeMinMaxTemp([
      { temp_celsius: Number.NaN },
      { temp_celsius: 200 },
    ]);
    expect(result).toEqual({ min: 200, max: 200 });
  });

  it("filters Infinity and uses remaining valid temps", () => {
    const result = computeMinMaxTemp([
      { temp_celsius: Infinity },
      { temp_celsius: 150 },
      { temp_celsius: -Infinity },
    ]);
    expect(result).toEqual({ min: 150, max: 150 });
  });

  it("filters undefined temp_celsius and returns fallback when all invalid", () => {
    const result = computeMinMaxTemp([{ temp_celsius: undefined }]);
    expect(result).toEqual({ min: THERMAL_MIN_TEMP, max: THERMAL_ABSOLUTE_MAX });
  });

  it("uses custom fallback when provided", () => {
    const result = computeMinMaxTemp([], 100, 500);
    expect(result).toEqual({ min: 100, max: 500 });
  });

  it("handles mixed valid and invalid points", () => {
    const result = computeMinMaxTemp([
      { temp_celsius: null },
      { temp_celsius: 300 },
      {},
      { temp_celsius: Number.NaN },
      { temp_celsius: 100 },
    ]);
    expect(result).toEqual({ min: 100, max: 300 });
  });
});
