/**
 * Tests for useSessionComparison hook (Step 14B).
 */

import { renderHook } from "@testing-library/react";
import type { Frame } from "@/types/frame";
import type { Session } from "@/types/session";
import type { ThermalSnapshot } from "@/types/thermal";
import {
  useSessionComparison,
  compareSessions,
  deltaOptional,
  computeThermalDeltas,
} from "@/hooks/useSessionComparison";

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
      { direction: "north", temp_celsius: centerTemp - 20 },
      { direction: "south", temp_celsius: centerTemp - 10 },
      { direction: "east", temp_celsius: centerTemp - 30 },
      { direction: "west", temp_celsius: centerTemp - 25 },
    ],
  };
}

function makeFrame(
  timestamp_ms: number,
  overrides: Partial<Frame> = {}
): Frame {
  return {
    timestamp_ms,
    volts: 22.5,
    amps: 150.0,
    angle_degrees: 45.0,
    thermal_snapshots: [],
    has_thermal_data: false,
    optional_sensors: null,
    heat_dissipation_rate_celsius_per_sec: null,
    ...overrides,
  };
}

function makeThermalFrame(
  timestamp_ms: number,
  centerTemp: number
): Frame {
  return makeFrame(timestamp_ms, {
    thermal_snapshots: [makeSnapshot(10.0, centerTemp)],
    has_thermal_data: true,
    heat_dissipation_rate_celsius_per_sec: -5.0,
  });
}

function makeSession(
  id: string,
  frames: Frame[],
  overrides: Partial<Session> = {}
): Session {
  return {
    session_id: id,
    operator_id: "op_42",
    start_time: "2026-02-07T10:00:00Z",
    weld_type: "mild_steel",
    thermal_sample_interval_ms: 100,
    thermal_directions: ["center", "north", "south", "east", "west"],
    thermal_distance_interval_mm: 10.0,
    sensor_sample_rate_hz: 100,
    frames,
    status: "complete",
    frame_count: frames.length,
    expected_frame_count: frames.length,
    last_successful_frame_index: frames.length > 0 ? frames.length - 1 : null,
    validation_errors: [],
    completed_at: "2026-02-07T10:01:00Z",
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// deltaOptional
// ---------------------------------------------------------------------------

describe("deltaOptional", () => {
  it("returns difference when both present", () => {
    expect(deltaOptional(10, 3)).toBe(7);
  });

  it("returns null when a is null", () => {
    expect(deltaOptional(null, 3)).toBeNull();
  });

  it("returns null when b is null", () => {
    expect(deltaOptional(10, null)).toBeNull();
  });

  it("returns null when both null", () => {
    expect(deltaOptional(null, null)).toBeNull();
  });

  it("handles negative results", () => {
    expect(deltaOptional(3, 10)).toBe(-7);
  });

  it("returns 0 when equal", () => {
    expect(deltaOptional(5, 5)).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// computeThermalDeltas
// ---------------------------------------------------------------------------

describe("computeThermalDeltas", () => {
  it("returns empty when either frame has no thermal data", () => {
    const frameA = makeFrame(100);
    const frameB = makeThermalFrame(100, 400);
    expect(computeThermalDeltas(frameA, frameB)).toEqual([]);
    expect(computeThermalDeltas(frameB, frameA)).toEqual([]);
  });

  it("computes deltas for matching distances", () => {
    const frameA = makeThermalFrame(100, 500);
    const frameB = makeThermalFrame(100, 400);
    const deltas = computeThermalDeltas(frameA, frameB);
    expect(deltas).toHaveLength(1);
    expect(deltas[0].distance_mm).toBe(10.0);
    // center: 500 - 400 = 100
    const centerDelta = deltas[0].readings.find(
      (r) => r.direction === "center"
    );
    expect(centerDelta?.delta_temp_celsius).toBe(100);
  });

  it("skips distances only in one frame", () => {
    const frameA = makeFrame(100, {
      thermal_snapshots: [makeSnapshot(10.0, 500), makeSnapshot(20.0, 450)],
      has_thermal_data: true,
    });
    const frameB = makeFrame(100, {
      thermal_snapshots: [makeSnapshot(10.0, 400)],
      has_thermal_data: true,
    });
    const deltas = computeThermalDeltas(frameA, frameB);
    // Only distance 10.0 is shared
    expect(deltas).toHaveLength(1);
    expect(deltas[0].distance_mm).toBe(10.0);
  });
});

// ---------------------------------------------------------------------------
// compareSessions
// ---------------------------------------------------------------------------

describe("compareSessions", () => {
  it("produces deltas for shared timestamps", () => {
    const sessA = makeSession("a", [
      makeFrame(0, { amps: 100 }),
      makeFrame(10, { amps: 110 }),
      makeFrame(20, { amps: 120 }),
    ]);
    const sessB = makeSession("b", [
      makeFrame(0, { amps: 95 }),
      makeFrame(10, { amps: 105 }),
      makeFrame(20, { amps: 115 }),
    ]);
    const result = compareSessions(sessA, sessB);
    expect(result.shared_count).toBe(3);
    expect(result.deltas).toHaveLength(3);
    expect(result.deltas[0].amps_delta).toBe(5); // 100 - 95
    expect(result.deltas[1].amps_delta).toBe(5); // 110 - 105
  });

  it("handles sessions with different timestamps (partial overlap)", () => {
    const sessA = makeSession("a", [
      makeFrame(0),
      makeFrame(10),
      makeFrame(20),
    ]);
    const sessB = makeSession("b", [
      makeFrame(10),
      makeFrame(20),
      makeFrame(30),
    ]);
    const result = compareSessions(sessA, sessB);
    expect(result.shared_count).toBe(2); // 10 and 20
    expect(result.only_in_a_count).toBe(1); // 0
    expect(result.only_in_b_count).toBe(1); // 30
  });

  it("handles no overlap (returns empty deltas)", () => {
    const sessA = makeSession("a", [makeFrame(0), makeFrame(10)]);
    const sessB = makeSession("b", [makeFrame(100), makeFrame(110)]);
    const result = compareSessions(sessA, sessB);
    expect(result.shared_count).toBe(0);
    expect(result.deltas).toEqual([]);
    expect(result.only_in_a_count).toBe(2);
    expect(result.only_in_b_count).toBe(2);
  });

  it("handles empty sessions", () => {
    const sessA = makeSession("a", []);
    const sessB = makeSession("b", []);
    const result = compareSessions(sessA, sessB);
    expect(result.shared_count).toBe(0);
    expect(result.total_a).toBe(0);
    expect(result.total_b).toBe(0);
  });

  it("handles sessions with different durations", () => {
    const sessA = makeSession("a", [
      makeFrame(0),
      makeFrame(10),
    ]);
    const sessB = makeSession("b", [
      makeFrame(0),
      makeFrame(10),
      makeFrame(20),
      makeFrame(30),
    ]);
    const result = compareSessions(sessA, sessB);
    expect(result.shared_count).toBe(2);
    expect(result.only_in_b_count).toBe(2);
    expect(result.total_a).toBe(2);
    expect(result.total_b).toBe(4);
  });

  it("works for expert vs expert (small deltas)", () => {
    const sessA = makeSession("expert1", [
      makeFrame(0, { volts: 22.5, amps: 150 }),
    ]);
    const sessB = makeSession("expert2", [
      makeFrame(0, { volts: 22.3, amps: 148 }),
    ]);
    const result = compareSessions(sessA, sessB);
    expect(result.deltas[0].volts_delta).toBeCloseTo(0.2);
    expect(result.deltas[0].amps_delta).toBe(2);
  });

  it("works for expert vs novice (large deltas)", () => {
    const sessA = makeSession("expert", [
      makeFrame(0, { volts: 22.5, amps: 150, angle_degrees: 45 }),
    ]);
    const sessB = makeSession("novice", [
      makeFrame(0, { volts: 18.0, amps: 200, angle_degrees: 60 }),
    ]);
    const result = compareSessions(sessA, sessB);
    expect(result.deltas[0].volts_delta).toBeCloseTo(4.5);
    expect(result.deltas[0].amps_delta).toBe(-50);
    expect(result.deltas[0].angle_degrees_delta).toBe(-15);
  });

  it("handles null sensor values (delta = null)", () => {
    const sessA = makeSession("a", [
      makeFrame(0, { volts: null, amps: 150 }),
    ]);
    const sessB = makeSession("b", [
      makeFrame(0, { volts: 22.0, amps: null }),
    ]);
    const result = compareSessions(sessA, sessB);
    expect(result.deltas[0].volts_delta).toBeNull();
    expect(result.deltas[0].amps_delta).toBeNull();
  });

  it("deltas are sorted by timestamp", () => {
    const sessA = makeSession("a", [
      makeFrame(20),
      makeFrame(0),
      makeFrame(10),
    ]);
    const sessB = makeSession("b", [
      makeFrame(10),
      makeFrame(0),
      makeFrame(20),
    ]);
    const result = compareSessions(sessA, sessB);
    expect(result.deltas.map((d) => d.timestamp_ms)).toEqual([0, 10, 20]);
  });
});

// ---------------------------------------------------------------------------
// useSessionComparison hook
// ---------------------------------------------------------------------------

describe("useSessionComparison", () => {
  it("returns null when sessionA is null", () => {
    const sessB = makeSession("b", [makeFrame(0)]);
    const { result } = renderHook(() => useSessionComparison(null, sessB));
    expect(result.current).toBeNull();
  });

  it("returns null when sessionB is null", () => {
    const sessA = makeSession("a", [makeFrame(0)]);
    const { result } = renderHook(() => useSessionComparison(sessA, null));
    expect(result.current).toBeNull();
  });

  it("returns null when both are null", () => {
    const { result } = renderHook(() => useSessionComparison(null, null));
    expect(result.current).toBeNull();
  });

  it("returns comparison result when both sessions provided", () => {
    const sessA = makeSession("a", [makeFrame(0), makeFrame(10)]);
    const sessB = makeSession("b", [makeFrame(0), makeFrame(10)]);
    const { result } = renderHook(() => useSessionComparison(sessA, sessB));
    expect(result.current).not.toBeNull();
    expect(result.current!.shared_count).toBe(2);
  });
});
