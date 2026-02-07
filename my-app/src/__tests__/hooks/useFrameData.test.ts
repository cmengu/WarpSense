/**
 * Tests for useFrameData hook (Step 14B).
 */

import { renderHook } from "@testing-library/react";
import type { Frame } from "@/types/frame";
import type { ThermalSnapshot } from "@/types/thermal";
import { useFrameData } from "@/hooks/useFrameData";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeSnapshot(distance_mm: number = 10.0): ThermalSnapshot {
  return {
    distance_mm,
    readings: [
      { direction: "center", temp_celsius: 400 },
      { direction: "north", temp_celsius: 380 },
      { direction: "south", temp_celsius: 390 },
      { direction: "east", temp_celsius: 370 },
      { direction: "west", temp_celsius: 375 },
    ],
  };
}

function makeSensorFrame(timestamp_ms: number): Frame {
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

function makeThermalFrame(timestamp_ms: number): Frame {
  return {
    timestamp_ms,
    volts: 22.5,
    amps: 150.0,
    angle_degrees: 45.0,
    thermal_snapshots: [makeSnapshot()],
    has_thermal_data: true,
    optional_sensors: null,
    heat_dissipation_rate_celsius_per_sec: -5.0,
  };
}

// ---------------------------------------------------------------------------
// useFrameData hook
// ---------------------------------------------------------------------------

describe("useFrameData", () => {
  it("returns counts for empty frames", () => {
    const { result } = renderHook(() => useFrameData([]));
    expect(result.current.total_count).toBe(0);
    expect(result.current.thermal_count).toBe(0);
    expect(result.current.has_any_thermal).toBe(false);
    expect(result.current.first_timestamp_ms).toBeNull();
    expect(result.current.last_timestamp_ms).toBeNull();
  });

  it("separates thermal and sensor-only frames", () => {
    const frames = [
      makeSensorFrame(0),
      makeSensorFrame(10),
      makeThermalFrame(100),
      makeSensorFrame(110),
      makeThermalFrame(200),
    ];
    const { result } = renderHook(() => useFrameData(frames));
    expect(result.current.total_count).toBe(5);
    expect(result.current.thermal_count).toBe(2);
    expect(result.current.has_any_thermal).toBe(true);
    expect(result.current.thermal_frames[0].timestamp_ms).toBe(100);
    expect(result.current.thermal_frames[1].timestamp_ms).toBe(200);
  });

  it("applies time range filter", () => {
    const frames = [
      makeSensorFrame(0),
      makeSensorFrame(10),
      makeSensorFrame(20),
      makeSensorFrame(30),
      makeSensorFrame(40),
    ];
    const { result } = renderHook(() => useFrameData(frames, 10, 30));
    expect(result.current.total_count).toBe(3);
    expect(result.current.first_timestamp_ms).toBe(10);
    expect(result.current.last_timestamp_ms).toBe(30);
  });

  it("filters thermal frames within time range", () => {
    const frames = [
      makeThermalFrame(100),
      makeSensorFrame(110),
      makeThermalFrame(200),
      makeSensorFrame(210),
      makeThermalFrame(300),
    ];
    const { result } = renderHook(() => useFrameData(frames, 100, 200));
    expect(result.current.total_count).toBe(3);
    expect(result.current.thermal_count).toBe(2);
  });

  it("null bounds mean unbounded", () => {
    const frames = [makeSensorFrame(0), makeSensorFrame(10)];
    const { result } = renderHook(() => useFrameData(frames, null, null));
    expect(result.current.total_count).toBe(2);
  });

  it("returns timestamps from filtered range", () => {
    const frames = [
      makeSensorFrame(0),
      makeSensorFrame(50),
      makeSensorFrame(100),
    ];
    const { result } = renderHook(() => useFrameData(frames, 50, null));
    expect(result.current.first_timestamp_ms).toBe(50);
    expect(result.current.last_timestamp_ms).toBe(100);
  });
});
