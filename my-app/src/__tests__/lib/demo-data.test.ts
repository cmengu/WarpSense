/**
 * Tests for demo-data.ts — browser-only demo session generation.
 *
 * Verifies that generateExpertSession and generateNoviceSession produce
 * valid Session objects with non-empty heatmap and angle data.
 * Critical for demo page: extractHeatmapData must receive frames that
 * yield point_count > 0.
 */

import { generateExpertSession, generateNoviceSession } from "@/lib/demo-data";
import { extractHeatmapData } from "@/utils/heatmapData";
import { extractAngleData } from "@/utils/angleData";

describe("demo-data", () => {
  describe("generateExpertSession", () => {
    it("returns session with 1500 frames (0–15000ms at 10ms interval)", () => {
      const session = generateExpertSession();
      expect(session.frames).toHaveLength(1500);
      expect(session.frame_count).toBe(1500);
    });

    it("produces non-empty heatmap data (extractHeatmapData point_count > 0)", () => {
      const session = generateExpertSession();
      const heatmap = extractHeatmapData(session.frames);
      expect(heatmap.point_count).toBeGreaterThan(0);
    });

    it("produces non-empty angle data (extractAngleData points.length > 0)", () => {
      const session = generateExpertSession();
      const angleData = extractAngleData(session.frames);
      expect(angleData.points.length).toBeGreaterThan(0);
    });

    it("has correct session metadata", () => {
      const session = generateExpertSession();
      expect(session.session_id).toBe("demo_expert");
      expect(session.status).toBe("complete");
      expect(session.thermal_sample_interval_ms).toBe(100);
    });
  });

  describe("generateNoviceSession", () => {
    it("returns session with 1500 frames (0–15000ms at 10ms interval)", () => {
      const session = generateNoviceSession();
      expect(session.frames).toHaveLength(1500);
      expect(session.frame_count).toBe(1500);
    });

    it("produces non-empty heatmap data (extractHeatmapData point_count > 0)", () => {
      const session = generateNoviceSession();
      const heatmap = extractHeatmapData(session.frames);
      expect(heatmap.point_count).toBeGreaterThan(0);
    });

    it("produces non-empty angle data (extractAngleData points.length > 0)", () => {
      const session = generateNoviceSession();
      const angleData = extractAngleData(session.frames);
      expect(angleData.points.length).toBeGreaterThan(0);
    });

    it("has correct session metadata", () => {
      const session = generateNoviceSession();
      expect(session.session_id).toBe("demo_novice");
      expect(session.status).toBe("complete");
    });
  });

  describe("frame structure", () => {
    it("frames have required fields (timestamp_ms, thermal_snapshots, has_thermal_data)", () => {
      const session = generateExpertSession();
      const thermalFrame = session.frames.find((f) => f.has_thermal_data);
      expect(thermalFrame).toBeDefined();
      if (!thermalFrame) throw new Error("thermalFrame not found");
      expect(thermalFrame.timestamp_ms).toBeGreaterThanOrEqual(0);
      expect(thermalFrame.thermal_snapshots.length).toBeGreaterThan(0);
      expect(thermalFrame.has_thermal_data).toBe(true);
    });

    it("thermal frames occur every 100ms", () => {
      const session = generateExpertSession();
      const thermalFrames = session.frames.filter((f) => f.has_thermal_data);
      const timestamps = thermalFrames.map((f) => f.timestamp_ms);
      for (let i = 1; i < timestamps.length; i++) {
        expect(timestamps[i] - timestamps[i - 1]).toBe(100);
      }
    });
  });
});
