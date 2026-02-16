/**
 * Tests for heatmapData.ts — extractHeatmapData utility.
 *
 * Verifies correct extraction of thermal data from frames into
 * the heatmap grid format (timestamp × distance → temperature).
 */

import {
  extractHeatmapData,
  tempToColor,
  tempToColorRange,
  type HeatmapDataPoint,
  type HeatmapData,
} from "@/utils/heatmapData";
import { temperatureToColor } from "@/utils/heatmapShaderUtils";
import type { Frame } from "@/types/frame";
import type { ThermalSnapshot } from "@/types/thermal";

/** RGB 0–1 to hex. */
function rgbToHex(r: number, g: number, b: number): string {
  const toHex = (c: number) =>
    Math.round(Math.max(0, Math.min(255, c * 255)))
      .toString(16)
      .padStart(2, "0");
  return "#" + toHex(r) + toHex(g) + toHex(b);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeSnapshot(
  distance_mm: number,
  centerTemp: number
): ThermalSnapshot {
  return {
    distance_mm,
    readings: [
      { direction: "center", temp_celsius: centerTemp },
      { direction: "north", temp_celsius: centerTemp - 10 },
      { direction: "south", temp_celsius: centerTemp - 5 },
      { direction: "east", temp_celsius: centerTemp - 15 },
      { direction: "west", temp_celsius: centerTemp - 12 },
    ],
  };
}

function makeThermalFrame(
  timestamp_ms: number,
  snapshots: ThermalSnapshot[]
): Frame {
  return {
    timestamp_ms,
    volts: 22.5,
    amps: 150.0,
    angle_degrees: 45.0,
    thermal_snapshots: snapshots,
    has_thermal_data: snapshots.length > 0,
    optional_sensors: null,
    heat_dissipation_rate_celsius_per_sec: null,
  };
}

function makeSensorOnlyFrame(timestamp_ms: number): Frame {
  return {
    timestamp_ms,
    volts: 22.0,
    amps: 148.0,
    angle_degrees: 44.0,
    thermal_snapshots: [],
    has_thermal_data: false,
    optional_sensors: null,
    heat_dissipation_rate_celsius_per_sec: null,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("extractHeatmapData", () => {
  describe("empty / no data", () => {
    it("returns empty result for empty frames array", () => {
      const result = extractHeatmapData([]);
      expect(result.points).toHaveLength(0);
      expect(result.timestamps_ms).toHaveLength(0);
      expect(result.distances_mm).toHaveLength(0);
      expect(result.point_count).toBe(0);
    });

    it("returns empty result when no frames have thermal data", () => {
      const frames = [
        makeSensorOnlyFrame(0),
        makeSensorOnlyFrame(10),
        makeSensorOnlyFrame(20),
      ];
      const result = extractHeatmapData(frames);
      expect(result.point_count).toBe(0);
    });
  });

  describe("single thermal frame", () => {
    it("extracts center direction by default", () => {
      const frame = makeThermalFrame(100, [
        makeSnapshot(10.0, 425.3),
        makeSnapshot(20.0, 430.1),
      ]);
      const result = extractHeatmapData([frame]);

      expect(result.point_count).toBe(2);
      expect(result.timestamps_ms).toEqual([100]);
      expect(result.distances_mm).toEqual([10.0, 20.0]);

      expect(result.points[0]).toEqual({
        timestamp_ms: 100,
        distance_mm: 10.0,
        temp_celsius: 425.3,
        direction: "center",
      });
      expect(result.points[1]).toEqual({
        timestamp_ms: 100,
        distance_mm: 20.0,
        temp_celsius: 430.1,
        direction: "center",
      });
    });
  });

  describe("direction filtering", () => {
    it("extracts north direction when specified", () => {
      const frame = makeThermalFrame(100, [makeSnapshot(10.0, 425.3)]);
      const result = extractHeatmapData([frame], "north");

      expect(result.point_count).toBe(1);
      // north = centerTemp - 10 = 415.3
      expect(result.points[0].temp_celsius).toBe(415.3);
      expect(result.points[0].direction).toBe("north");
    });

    it("extracts south direction when specified", () => {
      const frame = makeThermalFrame(100, [makeSnapshot(10.0, 400.0)]);
      const result = extractHeatmapData([frame], "south");

      expect(result.point_count).toBe(1);
      // south = centerTemp - 5 = 395.0
      expect(result.points[0].temp_celsius).toBe(395.0);
    });

    it("extracts east direction when specified", () => {
      const frame = makeThermalFrame(100, [makeSnapshot(10.0, 400.0)]);
      const result = extractHeatmapData([frame], "east");

      expect(result.point_count).toBe(1);
      // east = centerTemp - 15 = 385.0
      expect(result.points[0].temp_celsius).toBe(385.0);
    });

    it("extracts west direction when specified", () => {
      const frame = makeThermalFrame(100, [makeSnapshot(10.0, 400.0)]);
      const result = extractHeatmapData([frame], "west");

      expect(result.point_count).toBe(1);
      // west = centerTemp - 12 = 388.0
      expect(result.points[0].temp_celsius).toBe(388.0);
    });
  });

  describe("multiple frames", () => {
    it("extracts data from multiple thermal frames", () => {
      const frames = [
        makeThermalFrame(100, [
          makeSnapshot(10.0, 425.0),
          makeSnapshot(20.0, 430.0),
        ]),
        makeThermalFrame(200, [
          makeSnapshot(10.0, 420.0),
          makeSnapshot(20.0, 425.0),
        ]),
      ];
      const result = extractHeatmapData(frames);

      expect(result.point_count).toBe(4);
      expect(result.timestamps_ms).toEqual([100, 200]);
      expect(result.distances_mm).toEqual([10.0, 20.0]);
    });

    it("skips non-thermal frames in mixed array", () => {
      const frames = [
        makeSensorOnlyFrame(0),
        makeSensorOnlyFrame(10),
        makeThermalFrame(100, [makeSnapshot(10.0, 425.0)]),
        makeSensorOnlyFrame(110),
        makeSensorOnlyFrame(120),
        makeThermalFrame(200, [makeSnapshot(10.0, 420.0)]),
      ];
      const result = extractHeatmapData(frames);

      expect(result.point_count).toBe(2);
      expect(result.timestamps_ms).toEqual([100, 200]);
    });
  });

  describe("sorted outputs", () => {
    it("returns timestamps sorted ascending", () => {
      const frames = [
        makeThermalFrame(300, [makeSnapshot(10.0, 400.0)]),
        makeThermalFrame(100, [makeSnapshot(10.0, 425.0)]),
        makeThermalFrame(200, [makeSnapshot(10.0, 420.0)]),
      ];
      const result = extractHeatmapData(frames);
      expect(result.timestamps_ms).toEqual([100, 200, 300]);
    });

    it("returns distances sorted ascending", () => {
      const frame = makeThermalFrame(100, [
        makeSnapshot(30.0, 400.0),
        makeSnapshot(10.0, 425.0),
        makeSnapshot(20.0, 420.0),
      ]);
      const result = extractHeatmapData([frame]);
      expect(result.distances_mm).toEqual([10.0, 20.0, 30.0]);
    });
  });

  describe("edge cases", () => {
    it("handles snapshot with missing direction reading gracefully", () => {
      // Snapshot without a center reading — should produce 0 center points
      const frame: Frame = {
        timestamp_ms: 100,
        volts: 22.0,
        amps: 150.0,
        angle_degrees: 45.0,
        thermal_snapshots: [
          {
            distance_mm: 10.0,
            readings: [
              { direction: "north", temp_celsius: 380.0 },
              { direction: "south", temp_celsius: 390.0 },
              { direction: "east", temp_celsius: 370.0 },
              { direction: "west", temp_celsius: 375.0 },
              { direction: "north", temp_celsius: 382.0 }, // duplicate north, no center
            ],
          },
        ],
        has_thermal_data: true,
        optional_sensors: null,
        heat_dissipation_rate_celsius_per_sec: null,
      };
      const result = extractHeatmapData([frame], "center");
      expect(result.point_count).toBe(0);
    });

    it("handles single snapshot with single distance", () => {
      const frame = makeThermalFrame(0, [makeSnapshot(5.0, 500.0)]);
      const result = extractHeatmapData([frame]);

      expect(result.point_count).toBe(1);
      expect(result.timestamps_ms).toEqual([0]);
      expect(result.distances_mm).toEqual([5.0]);
    });

    it("de-duplicates timestamps and distances in index arrays", () => {
      // Two frames at the same timestamp (shouldn't happen, but be safe)
      const frames = [
        makeThermalFrame(100, [makeSnapshot(10.0, 425.0)]),
        makeThermalFrame(100, [makeSnapshot(10.0, 430.0)]),
      ];
      const result = extractHeatmapData(frames);

      // Points: 2 (one per frame)
      expect(result.point_count).toBe(2);
      // But unique timestamps/distances: 1 each
      expect(result.timestamps_ms).toEqual([100]);
      expect(result.distances_mm).toEqual([10.0]);
    });
  });

  describe("tempToColor", () => {
    it("returns dark blue (#1e3a8a) at 0°C", () => {
      expect(tempToColor(0).toLowerCase()).toBe("#1e3a8a");
    });

    it("returns violet (#7c3aed) at 250°C", () => {
      expect(tempToColor(250).toLowerCase()).toBe("#7c3aed");
    });

    it("returns purple (#a855f7) at 500°C", () => {
      expect(tempToColor(500).toLowerCase()).toBe("#a855f7");
    });

    it("interpolates between anchors", () => {
      const low = tempToColor(100);
      const mid = tempToColor(310);
      const high = tempToColor(450);
      expect(low).toMatch(/^#[0-9a-f]{6}$/i);
      expect(mid).toMatch(/^#[0-9a-f]{6}$/i);
      expect(high).toMatch(/^#[0-9a-f]{6}$/i);
    });

    it("clamps temps below 0 to 0", () => {
      expect(tempToColor(-50).toLowerCase()).toBe("#1e3a8a");
    });

    it("clamps temps above 500 to 500", () => {
      expect(tempToColor(800).toLowerCase()).toBe("#a855f7");
    });

    it("expert ~490°C yields purple-ish (b > r)", () => {
      const color = tempToColor(490).toLowerCase();
      const r = parseInt(color.slice(1, 3), 16);
      const b = parseInt(color.slice(5, 7), 16);
      expect(b).toBeGreaterThan(r);
      expect(r).toBeGreaterThan(100);
    });

    it("novice spike ~520°C yields purple-ish (clamped to 500)", () => {
      const color520 = tempToColor(520).toLowerCase();
      const r = parseInt(color520.slice(1, 3), 16);
      const b = parseInt(color520.slice(5, 7), 16);
      expect(b).toBeGreaterThan(r);
      expect(r).toBeGreaterThan(100);
    });
  });

  describe("tempToColorRange", () => {
    it("maps min to blue and max to purple over the given range", () => {
      const fn = tempToColorRange(400, 550);
      const atMin = fn(400).toLowerCase();
      const atMax = fn(550).toLowerCase();
      expect(atMin).toBe("#1e3a8a");
      expect(atMax).toBe("#a855f7");
    });

    it("returns tempToColor when range is invalid (span <= 0)", () => {
      const fn = tempToColorRange(500, 500);
      expect(fn(450)).toBe(tempToColor(450));
    });
  });

  describe("thermal sync: heatmapData vs heatmapShaderUtils", () => {
    it("tempToColor and temperatureToColor produce matching colors for sample temps", () => {
      const samples = [0, 62, 125, 250, 375, 500];
      for (const t of samples) {
        const hexFromHeatmap = tempToColor(t).toLowerCase();
        const [r, g, b] = temperatureToColor(0, 500, 10, t);
        const hexFromShader = rgbToHex(r, g, b).toLowerCase();
        const r1 = parseInt(hexFromHeatmap.slice(1, 3), 16);
        const g1 = parseInt(hexFromHeatmap.slice(3, 5), 16);
        const b1 = parseInt(hexFromHeatmap.slice(5, 7), 16);
        const r2 = Math.round(r * 255);
        const g2 = Math.round(g * 255);
        const b2 = Math.round(b * 255);
        expect(Math.abs(r1 - r2)).toBeLessThanOrEqual(2);
        expect(Math.abs(g1 - g2)).toBeLessThanOrEqual(2);
        expect(Math.abs(b1 - b2)).toBeLessThanOrEqual(2);
      }
    });
  });

  describe("return type structure", () => {
    it("returns the correct HeatmapData shape", () => {
      const result = extractHeatmapData([]);
      expect(result).toHaveProperty("points");
      expect(result).toHaveProperty("timestamps_ms");
      expect(result).toHaveProperty("distances_mm");
      expect(result).toHaveProperty("point_count");
      expect(Array.isArray(result.points)).toBe(true);
      expect(Array.isArray(result.timestamps_ms)).toBe(true);
      expect(Array.isArray(result.distances_mm)).toBe(true);
      expect(typeof result.point_count).toBe("number");
    });

    it("each point has required HeatmapDataPoint fields", () => {
      const frame = makeThermalFrame(100, [makeSnapshot(10.0, 425.0)]);
      const result = extractHeatmapData([frame]);

      const point = result.points[0];
      expect(point).toHaveProperty("timestamp_ms");
      expect(point).toHaveProperty("distance_mm");
      expect(point).toHaveProperty("temp_celsius");
      expect(point).toHaveProperty("direction");
      expect(typeof point.timestamp_ms).toBe("number");
      expect(typeof point.distance_mm).toBe("number");
      expect(typeof point.temp_celsius).toBe("number");
      expect(typeof point.direction).toBe("string");
    });
  });
});
