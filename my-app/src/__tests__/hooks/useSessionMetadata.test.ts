/**
 * Tests for useSessionMetadata hook (Step 14B).
 */

import { renderHook } from "@testing-library/react";
import type { Session } from "@/types/session";
import type { Frame } from "@/types/frame";
import {
  useSessionMetadata,
  formatDuration,
  formatStartTime,
  getWeldTypeLabel,
} from "@/hooks/useSessionMetadata";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeFrame(timestamp_ms: number): Frame {
  return {
    timestamp_ms,
    volts: 22.5,
    amps: 150.0,
    angle_degrees: 45.0,
    thermal_snapshots: [],
    has_thermal_data: false,
    optional_sensors: null,
    heat_dissipation_rate_celsius_per_sec: null,
  };
}

function makeSession(overrides: Partial<Session> = {}): Session {
  return {
    session_id: "sess_001",
    operator_id: "op_42",
    start_time: "2026-02-07T10:00:00Z",
    weld_type: "mild_steel",
    thermal_sample_interval_ms: 100,
    thermal_directions: ["center", "north", "south", "east", "west"],
    thermal_distance_interval_mm: 10.0,
    sensor_sample_rate_hz: 100,
    frames: [makeFrame(0), makeFrame(10), makeFrame(20)],
    status: "recording",
    frame_count: 3,
    expected_frame_count: null,
    last_successful_frame_index: null,
    validation_errors: [],
    completed_at: null,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// formatDuration
// ---------------------------------------------------------------------------

describe("formatDuration", () => {
  it("formats 0ms as '0s'", () => {
    expect(formatDuration(0)).toBe("0s");
  });

  it("formats seconds only", () => {
    expect(formatDuration(45000)).toBe("45s");
  });

  it("formats minutes and seconds", () => {
    expect(formatDuration(90000)).toBe("1m 30s");
  });

  it("formats minutes only (no remainder seconds)", () => {
    expect(formatDuration(120000)).toBe("2m");
  });

  it("formats 5 minutes (max session)", () => {
    expect(formatDuration(300000)).toBe("5m");
  });

  it("handles negative as '0s'", () => {
    expect(formatDuration(-1000)).toBe("0s");
  });
});

// ---------------------------------------------------------------------------
// formatStartTime
// ---------------------------------------------------------------------------

describe("formatStartTime", () => {
  it("formats a valid date", () => {
    const date = new Date("2026-02-07T10:00:00Z");
    const result = formatStartTime(date);
    expect(result).toContain("2026");
    expect(result).toContain("Feb");
  });

  it("returns 'Invalid date' for null", () => {
    expect(formatStartTime(null)).toBe("Invalid date");
  });

  it("returns 'Invalid date' for invalid Date object", () => {
    expect(formatStartTime(new Date("not-a-date"))).toBe("Invalid date");
  });
});

// ---------------------------------------------------------------------------
// getWeldTypeLabel
// ---------------------------------------------------------------------------

describe("getWeldTypeLabel", () => {
  it("returns label for known metal type", () => {
    expect(getWeldTypeLabel("mild_steel")).toBe("Mild Steel");
    expect(getWeldTypeLabel("aluminum")).toBe("Aluminum");
  });

  it("returns raw value for unknown weld type", () => {
    expect(getWeldTypeLabel("butt_joint")).toBe("butt_joint");
    expect(getWeldTypeLabel("custom_type")).toBe("custom_type");
  });
});

// ---------------------------------------------------------------------------
// useSessionMetadata hook
// ---------------------------------------------------------------------------

describe("useSessionMetadata", () => {
  it("returns null when session is null", () => {
    const { result } = renderHook(() => useSessionMetadata(null));
    expect(result.current).toBeNull();
  });

  it("returns metadata for a valid session", () => {
    const session = makeSession();
    const { result } = renderHook(() => useSessionMetadata(session));
    const meta = result.current!;

    expect(meta.session_id).toBe("sess_001");
    expect(meta.operator_id).toBe("op_42");
    expect(meta.weld_type).toBe("mild_steel");
    expect(meta.weld_type_label).toBe("Mild Steel");
    expect(meta.status).toBe("recording");
    expect(meta.frame_count).toBe(3);
    expect(meta.is_recording).toBe(true);
    expect(meta.is_complete).toBe(false);
  });

  it("computes duration from last frame timestamp", () => {
    const session = makeSession({
      frames: [makeFrame(0), makeFrame(10), makeFrame(90000)],
      frame_count: 3,
    });
    const { result } = renderHook(() => useSessionMetadata(session));
    expect(result.current!.duration_ms).toBe(90000);
    expect(result.current!.duration_display).toBe("1m 30s");
  });

  it("handles empty frames (duration = 0)", () => {
    const session = makeSession({ frames: [], frame_count: 0 });
    const { result } = renderHook(() => useSessionMetadata(session));
    expect(result.current!.duration_ms).toBe(0);
    expect(result.current!.duration_display).toBe("0s");
  });

  it("parses start_time into a Date", () => {
    const session = makeSession({ start_time: "2026-02-07T10:00:00Z" });
    const { result } = renderHook(() => useSessionMetadata(session));
    expect(result.current!.start_date).toBeInstanceOf(Date);
    expect(result.current!.start_time_display).toContain("2026");
  });

  it("handles unparseable start_time", () => {
    const session = makeSession({ start_time: "not-a-date" });
    const { result } = renderHook(() => useSessionMetadata(session));
    expect(result.current!.start_date).toBeNull();
    expect(result.current!.start_time_display).toBe("Invalid date");
  });

  it("sets is_complete for complete sessions", () => {
    const session = makeSession({
      status: "complete",
      expected_frame_count: 3,
      last_successful_frame_index: 2,
      completed_at: "2026-02-07T10:01:00Z",
    });
    const { result } = renderHook(() => useSessionMetadata(session));
    expect(result.current!.is_complete).toBe(true);
    expect(result.current!.is_recording).toBe(false);
  });

  it("passes through validation_errors", () => {
    const session = makeSession({
      validation_errors: ["error1", "error2"],
    });
    const { result } = renderHook(() => useSessionMetadata(session));
    expect(result.current!.validation_errors).toEqual(["error1", "error2"]);
  });
});
