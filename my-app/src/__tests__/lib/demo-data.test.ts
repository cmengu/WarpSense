/**
 * Tests for demo-data.ts — browser-only demo session generation.
 *
 * Verifies that generateExpertSession and generateNoviceSession produce
 * valid Session objects with non-empty heatmap and angle data.
 * Critical for demo page: extractHeatmapData must receive frames that
 * yield point_count > 0.
 */

import { generateExpertSession, generateNoviceSession } from "@/lib/demo-data";
import {
  AL_TRAVEL_SPEED_EXPERT_MIN,
  AL_TRAVEL_SPEED_EXPERT_MAX,
} from "@/constants/aluminum";
import { extractHeatmapData } from "@/utils/heatmapData";
import { extractAngleData } from "@/utils/angleData";
import {
  extractCenterTemperatureWithCarryForward,
  getFrameAtTimestamp,
} from "@/utils/frameUtils";

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

    it("expert travel_speed_mm_per_min spans 370–430", () => {
      const expert = generateExpertSession();
      const speeds = expert.frames.map((f) => f.travel_speed_mm_per_min!);
      expect(Math.min(...speeds)).toBeGreaterThanOrEqual(AL_TRAVEL_SPEED_EXPERT_MIN);
      expect(Math.max(...speeds)).toBeLessThanOrEqual(AL_TRAVEL_SPEED_EXPERT_MAX);
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

    it("novice travel_speed_mm_per_min spans below 300 and above 500", () => {
      const novice = generateNoviceSession();
      const speeds = novice.frames.map((f) => f.travel_speed_mm_per_min!);
      expect(Math.min(...speeds)).toBeLessThan(300);
      expect(Math.max(...speeds)).toBeGreaterThan(500);
    });

    it("has correct session metadata", () => {
      const session = generateNoviceSession();
      expect(session.session_id).toBe("demo_novice");
      expect(session.status).toBe("complete");
    });
  });

  describe("frame structure", () => {
    it("frames have required fields (timestamp_ms, thermal_snapshots, has_thermal_data, travel_speed_mm_per_min)", () => {
      const session = generateExpertSession();
      for (const f of session.frames) {
        expect(f.travel_speed_mm_per_min).not.toBeNull();
        expect(f.travel_speed_mm_per_min).not.toBeUndefined();
      }
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

  describe("integration with frameUtils", () => {
    it("extractCenterTemperatureWithCarryForward returns finite temps for expert", () => {
      const session = generateExpertSession();
      const t0 = extractCenterTemperatureWithCarryForward(session.frames, 0);
      const t5000 = extractCenterTemperatureWithCarryForward(session.frames, 5000);
      const t14990 = extractCenterTemperatureWithCarryForward(
        session.frames,
        14990
      );
      expect(Number.isFinite(t0)).toBe(true);
      expect(t0).toBeGreaterThan(100);
      expect(t0).toBeLessThan(800);
      expect(Number.isFinite(t5000)).toBe(true);
      expect(Number.isFinite(t14990)).toBe(true);
    });

    it("getFrameAtTimestamp returns correct frame for expert", () => {
      const session = generateExpertSession();
      const f0 = getFrameAtTimestamp(session.frames, 0);
      const f100 = getFrameAtTimestamp(session.frames, 100);
      const f99 = getFrameAtTimestamp(session.frames, 99);
      expect(f0).not.toBeNull();
      expect(f0?.timestamp_ms).toBe(0);
      expect(f100).not.toBeNull();
      expect(f100?.timestamp_ms).toBe(100);
      expect(f99?.timestamp_ms).toBe(90); // nearest frame at or before 99
    });
  });
});
