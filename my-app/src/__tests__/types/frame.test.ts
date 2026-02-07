/**
 * Tests for frontend Frame type (Step 10).
 *
 * Validates:
 *   - Frame interface structure and snake_case naming
 *   - has_thermal_data consistency with thermal_snapshots
 *   - Optional field null handling (volts, amps, angle_degrees, etc.)
 *   - Thermal snapshot distance ordering validation
 *   - validateFrame() comprehensive runtime checks
 *   - Edge cases: first frame, sensor-only frame, partial sensors
 */

import type { ThermalSnapshot } from "@/types/thermal";
import type { Frame } from "@/types/frame";
import { validateFrame } from "@/types/frame";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a valid set of 5 thermal readings. */
function makeReadings(baseTemp: number = 400.0) {
  return [
    { direction: "center" as const, temp_celsius: baseTemp },
    { direction: "north" as const, temp_celsius: baseTemp - 20 },
    { direction: "south" as const, temp_celsius: baseTemp - 10 },
    { direction: "east" as const, temp_celsius: baseTemp - 30 },
    { direction: "west" as const, temp_celsius: baseTemp - 25 },
  ];
}

/** Build a valid thermal snapshot at a given distance. */
function makeSnapshot(distance_mm: number, baseTemp: number = 400.0): ThermalSnapshot {
  return { distance_mm, readings: makeReadings(baseTemp) };
}

/** Build a valid frame with thermal data. */
function makeThermalFrame(overrides: Partial<Frame> = {}): Frame {
  return {
    timestamp_ms: 100,
    volts: 22.5,
    amps: 150.0,
    angle_degrees: 45.0,
    thermal_snapshots: [makeSnapshot(10.0)],
    has_thermal_data: true,
    optional_sensors: null,
    heat_dissipation_rate_celsius_per_sec: -5.2,
    ...overrides,
  };
}

/** Build a valid frame without thermal data (sensor-only). */
function makeSensorOnlyFrame(overrides: Partial<Frame> = {}): Frame {
  return {
    timestamp_ms: 10,
    volts: 22.4,
    amps: 149.5,
    angle_degrees: 44.8,
    thermal_snapshots: [],
    has_thermal_data: false,
    optional_sensors: null,
    heat_dissipation_rate_celsius_per_sec: null,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Frame structure — snake_case naming
// ---------------------------------------------------------------------------

describe("Frame interface — snake_case field names matching backend", () => {
  it("thermal frame has all expected keys", () => {
    const frame = makeThermalFrame();
    const keys = Object.keys(frame);
    expect(keys).toContain("timestamp_ms");
    expect(keys).toContain("volts");
    expect(keys).toContain("amps");
    expect(keys).toContain("angle_degrees");
    expect(keys).toContain("thermal_snapshots");
    expect(keys).toContain("has_thermal_data");
    expect(keys).toContain("optional_sensors");
    expect(keys).toContain("heat_dissipation_rate_celsius_per_sec");
  });

  it("sensor-only frame has all expected keys", () => {
    const frame = makeSensorOnlyFrame();
    const keys = Object.keys(frame);
    expect(keys).toContain("timestamp_ms");
    expect(keys).toContain("has_thermal_data");
    expect(keys).toContain("heat_dissipation_rate_celsius_per_sec");
  });

  it("no camelCase keys exist (enforces snake_case contract)", () => {
    const frame = makeThermalFrame();
    const keys = Object.keys(frame);
    // These camelCase equivalents must NOT exist
    expect(keys).not.toContain("timestampMs");
    expect(keys).not.toContain("angleDegrees");
    expect(keys).not.toContain("thermalSnapshots");
    expect(keys).not.toContain("hasThermalData");
    expect(keys).not.toContain("optionalSensors");
    expect(keys).not.toContain("heatDissipationRateCelsiusPerSec");
  });
});

// ---------------------------------------------------------------------------
// has_thermal_data consistency
// ---------------------------------------------------------------------------

describe("has_thermal_data consistency", () => {
  it("is true when thermal_snapshots is non-empty", () => {
    const frame = makeThermalFrame();
    expect(frame.has_thermal_data).toBe(true);
    expect(frame.thermal_snapshots.length).toBeGreaterThan(0);
  });

  it("is false when thermal_snapshots is empty", () => {
    const frame = makeSensorOnlyFrame();
    expect(frame.has_thermal_data).toBe(false);
    expect(frame.thermal_snapshots).toHaveLength(0);
  });

  it("validateFrame catches mismatch: has_thermal_data=true but empty array", () => {
    const frame = makeSensorOnlyFrame({ has_thermal_data: true });
    const errors = validateFrame(frame);
    expect(errors.some((e) => e.includes("has_thermal_data is true"))).toBe(true);
  });

  it("validateFrame catches mismatch: has_thermal_data=false but non-empty array", () => {
    const frame = makeThermalFrame({ has_thermal_data: false });
    const errors = validateFrame(frame);
    expect(errors.some((e) => e.includes("has_thermal_data is false"))).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Optional sensor fields — null handling
// ---------------------------------------------------------------------------

describe("Optional sensor fields — null handling", () => {
  it("accepts all-null sensor readings (partial frame)", () => {
    const frame = makeSensorOnlyFrame({
      volts: null,
      amps: null,
      angle_degrees: null,
    });
    const errors = validateFrame(frame);
    expect(errors).toEqual([]);
  });

  it("accepts mixed null/present sensor readings", () => {
    const frame = makeSensorOnlyFrame({
      volts: 22.5,
      amps: null,
      angle_degrees: 45.0,
    });
    const errors = validateFrame(frame);
    expect(errors).toEqual([]);
  });

  it("accepts all-present sensor readings", () => {
    const frame = makeSensorOnlyFrame({
      volts: 22.5,
      amps: 150.0,
      angle_degrees: 45.0,
    });
    const errors = validateFrame(frame);
    expect(errors).toEqual([]);
  });

  it("heat_dissipation_rate_celsius_per_sec can be null (first frame)", () => {
    const frame = makeSensorOnlyFrame({
      heat_dissipation_rate_celsius_per_sec: null,
    });
    expect(frame.heat_dissipation_rate_celsius_per_sec).toBeNull();
    const errors = validateFrame(frame);
    expect(errors).toEqual([]);
  });

  it("heat_dissipation_rate_celsius_per_sec can be negative (heating)", () => {
    const frame = makeThermalFrame({
      heat_dissipation_rate_celsius_per_sec: -12.5,
    });
    expect(frame.heat_dissipation_rate_celsius_per_sec).toBe(-12.5);
    const errors = validateFrame(frame);
    expect(errors).toEqual([]);
  });

  it("heat_dissipation_rate_celsius_per_sec can be positive (cooling)", () => {
    const frame = makeThermalFrame({
      heat_dissipation_rate_celsius_per_sec: 8.3,
    });
    expect(frame.heat_dissipation_rate_celsius_per_sec).toBe(8.3);
    const errors = validateFrame(frame);
    expect(errors).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// optional_sensors field
// ---------------------------------------------------------------------------

describe("optional_sensors field", () => {
  it("null means all expected sensors present", () => {
    const frame = makeSensorOnlyFrame({ optional_sensors: null });
    expect(frame.optional_sensors).toBeNull();
  });

  it("accepts a map of sensor availability flags", () => {
    const frame = makeSensorOnlyFrame({
      optional_sensors: { ir_sensor: false, gyroscope: true },
    });
    expect(frame.optional_sensors).toEqual({
      ir_sensor: false,
      gyroscope: true,
    });
  });
});

// ---------------------------------------------------------------------------
// timestamp_ms validation
// ---------------------------------------------------------------------------

describe("timestamp_ms validation", () => {
  it("accepts timestamp_ms = 0 (first frame)", () => {
    const frame = makeSensorOnlyFrame({ timestamp_ms: 0 });
    const errors = validateFrame(frame);
    expect(errors).toEqual([]);
  });

  it("accepts large timestamp_ms (5 minutes = 300000ms)", () => {
    const frame = makeSensorOnlyFrame({ timestamp_ms: 300000 });
    const errors = validateFrame(frame);
    expect(errors).toEqual([]);
  });

  it("rejects negative timestamp_ms", () => {
    const frame = makeSensorOnlyFrame({ timestamp_ms: -1 });
    const errors = validateFrame(frame);
    expect(errors.some((e) => e.includes("non-negative integer"))).toBe(true);
  });

  it("rejects non-integer timestamp_ms", () => {
    const frame = makeSensorOnlyFrame({ timestamp_ms: 10.5 });
    const errors = validateFrame(frame);
    expect(errors.some((e) => e.includes("non-negative integer"))).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Thermal snapshot distance ordering
// ---------------------------------------------------------------------------

describe("Thermal snapshot distance ordering", () => {
  it("accepts single snapshot (no ordering needed)", () => {
    const frame = makeThermalFrame({
      thermal_snapshots: [makeSnapshot(10.0)],
    });
    const errors = validateFrame(frame);
    expect(errors).toEqual([]);
  });

  it("accepts multiple snapshots with strictly increasing distances", () => {
    const frame = makeThermalFrame({
      thermal_snapshots: [
        makeSnapshot(10.0),
        makeSnapshot(20.0),
        makeSnapshot(30.0),
      ],
    });
    const errors = validateFrame(frame);
    expect(errors).toEqual([]);
  });

  it("rejects duplicate distances", () => {
    const frame = makeThermalFrame({
      thermal_snapshots: [makeSnapshot(10.0), makeSnapshot(10.0)],
    });
    const errors = validateFrame(frame);
    expect(errors.some((e) => e.includes("strictly increasing"))).toBe(true);
  });

  it("rejects decreasing distances", () => {
    const frame = makeThermalFrame({
      thermal_snapshots: [makeSnapshot(20.0), makeSnapshot(10.0)],
    });
    const errors = validateFrame(frame);
    expect(errors.some((e) => e.includes("strictly increasing"))).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// validateFrame — valid frames
// ---------------------------------------------------------------------------

describe("validateFrame — valid frames", () => {
  it("returns no errors for a valid thermal frame", () => {
    const errors = validateFrame(makeThermalFrame());
    expect(errors).toEqual([]);
  });

  it("returns no errors for a valid sensor-only frame", () => {
    const errors = validateFrame(makeSensorOnlyFrame());
    expect(errors).toEqual([]);
  });

  it("returns no errors for first frame (timestamp=0, null dissipation)", () => {
    const frame = makeSensorOnlyFrame({
      timestamp_ms: 0,
      heat_dissipation_rate_celsius_per_sec: null,
    });
    const errors = validateFrame(frame);
    expect(errors).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// validateFrame — invalid numeric fields
// ---------------------------------------------------------------------------

describe("validateFrame — invalid numeric fields", () => {
  it("rejects Infinity in volts", () => {
    const frame = makeSensorOnlyFrame({ volts: Infinity });
    const errors = validateFrame(frame);
    expect(errors.some((e) => e.includes("volts"))).toBe(true);
  });

  it("rejects NaN in amps", () => {
    const frame = makeSensorOnlyFrame({ amps: NaN });
    const errors = validateFrame(frame);
    expect(errors.some((e) => e.includes("amps"))).toBe(true);
  });

  it("rejects -Infinity in angle_degrees", () => {
    const frame = makeSensorOnlyFrame({ angle_degrees: -Infinity });
    const errors = validateFrame(frame);
    expect(errors.some((e) => e.includes("angle_degrees"))).toBe(true);
  });

  it("rejects NaN in heat_dissipation_rate_celsius_per_sec", () => {
    const frame = makeThermalFrame({
      heat_dissipation_rate_celsius_per_sec: NaN,
    });
    const errors = validateFrame(frame);
    expect(
      errors.some((e) => e.includes("heat_dissipation_rate_celsius_per_sec"))
    ).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// validateFrame — thermal snapshot sub-validation
// ---------------------------------------------------------------------------

describe("validateFrame — thermal snapshot sub-validation", () => {
  it("propagates snapshot validation errors (e.g. wrong reading count)", () => {
    const badSnapshot: ThermalSnapshot = {
      distance_mm: 10.0,
      readings: [
        { direction: "center", temp_celsius: 425.3 },
        { direction: "north", temp_celsius: 380.1 },
        // Only 2 readings — should fail
      ],
    };
    const frame = makeThermalFrame({
      thermal_snapshots: [badSnapshot],
    });
    const errors = validateFrame(frame);
    expect(errors.some((e) => e.includes("thermal_snapshots[0]"))).toBe(true);
    expect(errors.some((e) => e.includes("exactly 5 elements"))).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Type-level compile-time checks
// ---------------------------------------------------------------------------

describe("Type-level compile-time safety", () => {
  it("Frame requires all mandatory fields", () => {
    // This test documents the full shape of the Frame interface.
    // If any field were removed from the interface, this would fail to compile.
    const frame: Frame = {
      timestamp_ms: 0,
      volts: null,
      amps: null,
      angle_degrees: null,
      thermal_snapshots: [],
      has_thermal_data: false,
      optional_sensors: null,
      heat_dissipation_rate_celsius_per_sec: null,
    };
    expect(Object.keys(frame)).toHaveLength(8);
  });

  it("thermal_snapshots uses ThermalSnapshot type from thermal.ts", () => {
    const snapshot: ThermalSnapshot = makeSnapshot(5.0);
    const frame = makeThermalFrame({ thermal_snapshots: [snapshot] });
    expect(frame.thermal_snapshots[0].distance_mm).toBe(5.0);
    expect(frame.thermal_snapshots[0].readings).toHaveLength(5);
  });
});
