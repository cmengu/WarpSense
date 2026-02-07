/**
 * Tests for angleData.ts — extractAngleData utility.
 *
 * Verifies correct extraction of torch angle time-series data
 * from frames, including statistics and edge cases.
 */

import {
  extractAngleData,
  type AngleDataPoint,
  type AngleData,
} from "@/utils/angleData";
import type { Frame } from "@/types/frame";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeFrame(
  timestamp_ms: number,
  angle_degrees: number | null
): Frame {
  return {
    timestamp_ms,
    volts: 22.0,
    amps: 150.0,
    angle_degrees,
    thermal_snapshots: [],
    has_thermal_data: false,
    optional_sensors: null,
    heat_dissipation_rate_celsius_per_sec: null,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("extractAngleData", () => {
  describe("empty / no data", () => {
    it("returns empty result for empty frames array", () => {
      const result = extractAngleData([]);
      expect(result.points).toHaveLength(0);
      expect(result.point_count).toBe(0);
      expect(result.min_angle_degrees).toBeNull();
      expect(result.max_angle_degrees).toBeNull();
      expect(result.avg_angle_degrees).toBeNull();
    });

    it("returns empty result when all frames have null angle", () => {
      const frames = [
        makeFrame(0, null),
        makeFrame(10, null),
        makeFrame(20, null),
      ];
      const result = extractAngleData(frames);
      expect(result.point_count).toBe(0);
      expect(result.min_angle_degrees).toBeNull();
      expect(result.max_angle_degrees).toBeNull();
      expect(result.avg_angle_degrees).toBeNull();
    });
  });

  describe("single frame", () => {
    it("extracts a single angle data point", () => {
      const result = extractAngleData([makeFrame(100, 45.0)]);

      expect(result.point_count).toBe(1);
      expect(result.points[0]).toEqual({
        timestamp_ms: 100,
        angle_degrees: 45.0,
      });
      expect(result.min_angle_degrees).toBe(45.0);
      expect(result.max_angle_degrees).toBe(45.0);
      expect(result.avg_angle_degrees).toBe(45.0);
    });
  });

  describe("multiple frames", () => {
    it("extracts data points and computes statistics", () => {
      const frames = [
        makeFrame(0, 40.0),
        makeFrame(10, 45.0),
        makeFrame(20, 50.0),
      ];
      const result = extractAngleData(frames);

      expect(result.point_count).toBe(3);
      expect(result.min_angle_degrees).toBe(40.0);
      expect(result.max_angle_degrees).toBe(50.0);
      expect(result.avg_angle_degrees).toBe(45.0);
    });

    it("skips frames with null angle", () => {
      const frames = [
        makeFrame(0, 40.0),
        makeFrame(10, null),
        makeFrame(20, 50.0),
        makeFrame(30, null),
        makeFrame(40, 45.0),
      ];
      const result = extractAngleData(frames);

      expect(result.point_count).toBe(3);
      expect(result.points.map((p) => p.timestamp_ms)).toEqual([0, 20, 40]);
      expect(result.min_angle_degrees).toBe(40.0);
      expect(result.max_angle_degrees).toBe(50.0);
      expect(result.avg_angle_degrees).toBe(45.0);
    });
  });

  describe("sorting", () => {
    it("returns points sorted by timestamp ascending", () => {
      // Provide frames out of order
      const frames = [
        makeFrame(300, 45.0),
        makeFrame(100, 40.0),
        makeFrame(200, 50.0),
      ];
      const result = extractAngleData(frames);

      expect(result.points.map((p) => p.timestamp_ms)).toEqual([
        100, 200, 300,
      ]);
    });
  });

  describe("statistics", () => {
    it("computes correct average for non-uniform values", () => {
      const frames = [
        makeFrame(0, 10.0),
        makeFrame(10, 20.0),
        makeFrame(20, 30.0),
        makeFrame(30, 40.0),
      ];
      const result = extractAngleData(frames);

      // avg = (10 + 20 + 30 + 40) / 4 = 25
      expect(result.avg_angle_degrees).toBe(25.0);
    });

    it("handles negative angles", () => {
      const frames = [
        makeFrame(0, -10.0),
        makeFrame(10, 10.0),
      ];
      const result = extractAngleData(frames);

      expect(result.min_angle_degrees).toBe(-10.0);
      expect(result.max_angle_degrees).toBe(10.0);
      expect(result.avg_angle_degrees).toBe(0.0);
    });

    it("handles zero angle", () => {
      const frames = [
        makeFrame(0, 0.0),
        makeFrame(10, 0.0),
      ];
      const result = extractAngleData(frames);

      expect(result.min_angle_degrees).toBe(0.0);
      expect(result.max_angle_degrees).toBe(0.0);
      expect(result.avg_angle_degrees).toBe(0.0);
    });

    it("handles identical angles (min === max)", () => {
      const frames = [
        makeFrame(0, 45.0),
        makeFrame(10, 45.0),
        makeFrame(20, 45.0),
      ];
      const result = extractAngleData(frames);

      expect(result.min_angle_degrees).toBe(45.0);
      expect(result.max_angle_degrees).toBe(45.0);
      expect(result.avg_angle_degrees).toBe(45.0);
    });
  });

  describe("return type structure", () => {
    it("returns the correct AngleData shape", () => {
      const result = extractAngleData([]);
      expect(result).toHaveProperty("points");
      expect(result).toHaveProperty("point_count");
      expect(result).toHaveProperty("min_angle_degrees");
      expect(result).toHaveProperty("max_angle_degrees");
      expect(result).toHaveProperty("avg_angle_degrees");
      expect(Array.isArray(result.points)).toBe(true);
      expect(typeof result.point_count).toBe("number");
    });

    it("each point has required AngleDataPoint fields", () => {
      const result = extractAngleData([makeFrame(100, 45.0)]);
      const point = result.points[0];

      expect(point).toHaveProperty("timestamp_ms");
      expect(point).toHaveProperty("angle_degrees");
      expect(typeof point.timestamp_ms).toBe("number");
      expect(typeof point.angle_degrees).toBe("number");
    });
  });

  describe("edge cases", () => {
    it("handles large number of frames", () => {
      // 1000 frames at 10ms intervals
      const frames: Frame[] = [];
      for (let i = 0; i < 1000; i++) {
        frames.push(makeFrame(i * 10, 45.0 + Math.sin(i * 0.1) * 5));
      }
      const result = extractAngleData(frames);
      expect(result.point_count).toBe(1000);
      expect(result.min_angle_degrees).not.toBeNull();
      expect(result.max_angle_degrees).not.toBeNull();
      expect(result.avg_angle_degrees).not.toBeNull();
    });

    it("handles very small angle differences", () => {
      const frames = [
        makeFrame(0, 45.0001),
        makeFrame(10, 45.0002),
        makeFrame(20, 45.0003),
      ];
      const result = extractAngleData(frames);

      expect(result.min_angle_degrees).toBe(45.0001);
      expect(result.max_angle_degrees).toBe(45.0003);
    });
  });
});
