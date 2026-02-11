/**
 * Tests for frontend utility functions (Step 14, Step 19).
 * This file proves that every frontend data utility behaves safely, predictably, and defensively no matter how messy the backend data gets.
 *
 * Validates:
 *   - extractCenterTemperature() — all edge cases
 *   - extractTemperatureByDirection() — all directions + edge cases
 *   - extractAllTemperatures() — normal and edge cases
 *   - extractHeatDissipation() — null, undefined, positive, negative
 *   - hasRequiredSensors() — all combinations, optional_sensors handling
 *   - filterThermalFrames() — mixed arrays, empty input
 *   - filterFramesByTimeRange() — inclusive bounds, null bounds
 *   - Data transformation edge cases: empty frames, missing data
 */

import type { Frame } from "@/types/frame";
import type { ThermalSnapshot } from "@/types/thermal";
import {
  extractCenterTemperature,
  extractTemperatureByDirection,
  extractAllTemperatures,
  extractHeatDissipation,
  hasRequiredSensors,
  filterThermalFrames,
  filterFramesByTimeRange,
} from "@/utils/frameUtils";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeReadings(baseTemp: number = 400.0) {
  return [
    { direction: "center" as const, temp_celsius: baseTemp },
    { direction: "north" as const, temp_celsius: baseTemp - 20 },
    { direction: "south" as const, temp_celsius: baseTemp - 10 },
    { direction: "east" as const, temp_celsius: baseTemp - 30 },
    { direction: "west" as const, temp_celsius: baseTemp - 25 },
  ];
}

function makeSnapshot(
  distance_mm: number = 10.0,
  baseTemp: number = 400.0
): ThermalSnapshot {
  return { distance_mm, readings: makeReadings(baseTemp) };
}

function makeThermalFrame(overrides: Partial<Frame> = {}): Frame {
  return {
    timestamp_ms: 100,
    volts: 22.5,
    amps: 150.0,
    angle_degrees: 45.0,
    thermal_snapshots: [makeSnapshot(10.0, 425.3)],
    has_thermal_data: true,
    optional_sensors: null,
    heat_dissipation_rate_celsius_per_sec: -5.2,
    ...overrides,
  };
}

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
// extractCenterTemperature
// ---------------------------------------------------------------------------

describe("extractCenterTemperature", () => {
  it("returns center temp from frame with thermal data", () => {
    const frame = makeThermalFrame();
    const temp = extractCenterTemperature(frame);
    // Center reading has baseTemp (425.3) in our helper
    expect(temp).toBe(425.3);
  });

  it("returns null when has_thermal_data is false", () => {
    const frame = makeSensorOnlyFrame();
    expect(extractCenterTemperature(frame)).toBeNull();
  });

  it("returns null when thermal_snapshots is undefined", () => {
    const frame = makeThermalFrame({
      thermal_snapshots: undefined as unknown as ThermalSnapshot[],
    });
    expect(extractCenterTemperature(frame)).toBeNull();
  });

  it("returns null when thermal_snapshots is empty array", () => {
    const frame = makeThermalFrame({
      thermal_snapshots: [],
      has_thermal_data: false,
    });
    expect(extractCenterTemperature(frame)).toBeNull();
  });

  it("returns null when readings array is empty", () => {
    const frame = makeThermalFrame({
      thermal_snapshots: [{ distance_mm: 10.0, readings: [] }],
    });
    expect(extractCenterTemperature(frame)).toBeNull();
  });

  it("returns null when no center reading exists", () => {
    const frame = makeThermalFrame({
      thermal_snapshots: [
        {
          distance_mm: 10.0,
          readings: [
            { direction: "north", temp_celsius: 380 },
            { direction: "south", temp_celsius: 390 },
            { direction: "east", temp_celsius: 370 },
            { direction: "west", temp_celsius: 375 },
            { direction: "north", temp_celsius: 385 }, // duplicate north, no center
          ],
        },
      ],
    });
    expect(extractCenterTemperature(frame)).toBeNull();
  });

  it("uses first snapshot (primary distance) for extraction", () => {
    const frame = makeThermalFrame({
      thermal_snapshots: [
        makeSnapshot(10.0, 500.0), // first = primary
        makeSnapshot(20.0, 300.0), // second
      ],
    });
    expect(extractCenterTemperature(frame)).toBe(500.0);
  });
});

// ---------------------------------------------------------------------------
// extractTemperatureByDirection
// ---------------------------------------------------------------------------

describe("extractTemperatureByDirection", () => {
  it("extracts center temperature", () => {
    const frame = makeThermalFrame();
    expect(extractTemperatureByDirection(frame, "center")).toBe(425.3);
  });

  it("extracts north temperature", () => {
    const frame = makeThermalFrame();
    // north = baseTemp - 20 = 425.3 - 20 = 405.3
    expect(extractTemperatureByDirection(frame, "north")).toBe(425.3 - 20);
  });

  it("extracts south temperature", () => {
    const frame = makeThermalFrame();
    expect(extractTemperatureByDirection(frame, "south")).toBe(425.3 - 10);
  });

  it("extracts east temperature", () => {
    const frame = makeThermalFrame();
    expect(extractTemperatureByDirection(frame, "east")).toBe(425.3 - 30);
  });

  it("extracts west temperature", () => {
    const frame = makeThermalFrame();
    expect(extractTemperatureByDirection(frame, "west")).toBe(425.3 - 25);
  });

  it("extracts from a specific snapshot index", () => {
    const frame = makeThermalFrame({
      thermal_snapshots: [
        makeSnapshot(10.0, 500.0),
        makeSnapshot(20.0, 300.0),
      ],
    });
    // snapshotIndex=1 → baseTemp=300
    expect(extractTemperatureByDirection(frame, "center", 1)).toBe(300.0);
  });

  it("returns null for out-of-bounds snapshot index", () => {
    const frame = makeThermalFrame();
    expect(extractTemperatureByDirection(frame, "center", 5)).toBeNull();
  });

  it("returns null when has_thermal_data is false", () => {
    const frame = makeSensorOnlyFrame();
    expect(extractTemperatureByDirection(frame, "center")).toBeNull();
  });

  it("returns null when direction not found", () => {
    const frame = makeThermalFrame({
      thermal_snapshots: [
        {
          distance_mm: 10.0,
          readings: [
            { direction: "north", temp_celsius: 380 },
            { direction: "south", temp_celsius: 390 },
            { direction: "east", temp_celsius: 370 },
            { direction: "west", temp_celsius: 375 },
            { direction: "north", temp_celsius: 385 },
          ],
        },
      ],
    });
    expect(extractTemperatureByDirection(frame, "center")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// extractAllTemperatures
// ---------------------------------------------------------------------------

describe("extractAllTemperatures", () => {
  it("returns all 5 readings from thermal frame", () => {
    const frame = makeThermalFrame();
    const temps = extractAllTemperatures(frame);
    expect(temps).toHaveLength(5);
    expect(temps.map((t) => t.direction)).toEqual(
      expect.arrayContaining(["center", "north", "south", "east", "west"])
    );
  });

  it("returns empty array from sensor-only frame", () => {
    const frame = makeSensorOnlyFrame();
    expect(extractAllTemperatures(frame)).toEqual([]);
  });

  it("returns readings from specific snapshot index", () => {
    const frame = makeThermalFrame({
      thermal_snapshots: [
        makeSnapshot(10.0, 500.0),
        makeSnapshot(20.0, 300.0),
      ],
    });
    const temps = extractAllTemperatures(frame, 1);
    expect(temps).toHaveLength(5);
    // Center of snapshot[1] should be 300.0
    const center = temps.find((t) => t.direction === "center");
    expect(center?.temp_celsius).toBe(300.0);
  });

  it("returns empty array for out-of-bounds snapshot index", () => {
    const frame = makeThermalFrame();
    expect(extractAllTemperatures(frame, 99)).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// extractHeatDissipation
// ---------------------------------------------------------------------------

describe("extractHeatDissipation", () => {
  it("returns dissipation rate when present", () => {
    const frame = makeThermalFrame({
      heat_dissipation_rate_celsius_per_sec: -5.2,
    });
    expect(extractHeatDissipation(frame)).toBe(-5.2);
  });

  it("returns null for first frame (no previous frame)", () => {
    const frame = makeSensorOnlyFrame({
      heat_dissipation_rate_celsius_per_sec: null,
    });
    expect(extractHeatDissipation(frame)).toBeNull();
  });

  it("returns null when heat_dissipation_rate_celsius_per_sec is undefined", () => {
    // Simulates omitted/malformed API response where field is absent (not null)
    const frame = makeThermalFrame();
    (frame as { heat_dissipation_rate_celsius_per_sec?: number | null })
      .heat_dissipation_rate_celsius_per_sec = undefined;
    expect(extractHeatDissipation(frame)).toBeNull();
  });

  it("returns rate when set (e.g. 200.5)", () => {
    const frame = makeThermalFrame({
      heat_dissipation_rate_celsius_per_sec: 200.5,
    });
    expect(extractHeatDissipation(frame)).toBe(200.5);
  });

  it("returns positive value for cooling", () => {
    const frame = makeThermalFrame({
      heat_dissipation_rate_celsius_per_sec: 8.3,
    });
    expect(extractHeatDissipation(frame)).toBe(8.3);
  });

  it("returns negative value for heating", () => {
    const frame = makeThermalFrame({
      heat_dissipation_rate_celsius_per_sec: -12.5,
    });
    expect(extractHeatDissipation(frame)).toBe(-12.5);
  });

  it("returns zero for no change", () => {
    const frame = makeThermalFrame({
      heat_dissipation_rate_celsius_per_sec: 0,
    });
    expect(extractHeatDissipation(frame)).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// hasRequiredSensors
// ---------------------------------------------------------------------------

describe("hasRequiredSensors", () => {
  it("returns true when all three sensors present", () => {
    const frame = makeSensorOnlyFrame({
      volts: 22.5,
      amps: 150.0,
      angle_degrees: 45.0,
    });
    expect(hasRequiredSensors(frame)).toBe(true);
  });

  it("returns false when volts is null", () => {
    const frame = makeSensorOnlyFrame({ volts: null });
    expect(hasRequiredSensors(frame)).toBe(false);
  });

  it("returns false when amps is null", () => {
    const frame = makeSensorOnlyFrame({ amps: null });
    expect(hasRequiredSensors(frame)).toBe(false);
  });

  it("returns false when angle_degrees is null", () => {
    const frame = makeSensorOnlyFrame({ angle_degrees: null });
    expect(hasRequiredSensors(frame)).toBe(false);
  });

  it("returns false when all three are null", () => {
    const frame = makeSensorOnlyFrame({
      volts: null,
      amps: null,
      angle_degrees: null,
    });
    expect(hasRequiredSensors(frame)).toBe(false);
  });

  it("returns true even with zero values (zero is a valid reading)", () => {
    const frame = makeSensorOnlyFrame({
      volts: 0,
      amps: 0,
      angle_degrees: 0,
    });
    expect(hasRequiredSensors(frame)).toBe(true);
  });

  it("returns true when optional_sensors is null (does not affect check)", () => {
    const frame = makeSensorOnlyFrame({
      optional_sensors: null,
      volts: 22.5,
      amps: 150.0,
      angle_degrees: 45.0,
    });
    expect(hasRequiredSensors(frame)).toBe(true);
  });

  it("returns true when optional_sensors is undefined (does not affect check)", () => {
    const frame = makeSensorOnlyFrame({
      volts: 22.5,
      amps: 150.0,
      angle_degrees: 45.0,
    });
    (frame as { optional_sensors?: Record<string, boolean> | null }).optional_sensors =
      undefined;
    expect(hasRequiredSensors(frame)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// filterThermalFrames
// ---------------------------------------------------------------------------

describe("filterThermalFrames", () => {
  it("returns only frames with thermal data", () => {
    const frames = [
      makeSensorOnlyFrame({ timestamp_ms: 0 }),
      makeSensorOnlyFrame({ timestamp_ms: 10 }),
      makeThermalFrame({ timestamp_ms: 100 }),
      makeSensorOnlyFrame({ timestamp_ms: 110 }),
      makeThermalFrame({ timestamp_ms: 200 }),
    ];
    const thermal = filterThermalFrames(frames);
    expect(thermal).toHaveLength(2);
    expect(thermal[0].timestamp_ms).toBe(100);
    expect(thermal[1].timestamp_ms).toBe(200);
  });

  it("returns empty array when no frames have thermal data", () => {
    const frames = [
      makeSensorOnlyFrame({ timestamp_ms: 0 }),
      makeSensorOnlyFrame({ timestamp_ms: 10 }),
    ];
    expect(filterThermalFrames(frames)).toEqual([]);
  });

  it("returns all frames when all have thermal data", () => {
    const frames = [
      makeThermalFrame({ timestamp_ms: 100 }),
      makeThermalFrame({ timestamp_ms: 200 }),
    ];
    expect(filterThermalFrames(frames)).toHaveLength(2);
  });

  it("returns empty array for empty input", () => {
    expect(filterThermalFrames([])).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// filterFramesByTimeRange
// ---------------------------------------------------------------------------

describe("filterFramesByTimeRange", () => {
  const frames = [
    makeSensorOnlyFrame({ timestamp_ms: 0 }),
    makeSensorOnlyFrame({ timestamp_ms: 10 }),
    makeSensorOnlyFrame({ timestamp_ms: 20 }),
    makeSensorOnlyFrame({ timestamp_ms: 30 }),
    makeSensorOnlyFrame({ timestamp_ms: 40 }),
  ];

  it("filters by start and end (inclusive)", () => {
    const result = filterFramesByTimeRange(frames, 10, 30);
    expect(result).toHaveLength(3);
    expect(result[0].timestamp_ms).toBe(10);
    expect(result[2].timestamp_ms).toBe(30);
  });

  it("null startMs means no lower bound", () => {
    const result = filterFramesByTimeRange(frames, null, 20);
    expect(result).toHaveLength(3);
    expect(result[0].timestamp_ms).toBe(0);
    expect(result[2].timestamp_ms).toBe(20);
  });

  it("null endMs means no upper bound", () => {
    const result = filterFramesByTimeRange(frames, 20, null);
    expect(result).toHaveLength(3);
    expect(result[0].timestamp_ms).toBe(20);
    expect(result[2].timestamp_ms).toBe(40);
  });

  it("both null means return all frames", () => {
    const result = filterFramesByTimeRange(frames, null, null);
    expect(result).toHaveLength(5);
  });

  it("returns empty array when range matches nothing", () => {
    const result = filterFramesByTimeRange(frames, 100, 200);
    expect(result).toEqual([]);
  });

  it("returns single frame when range is exact", () => {
    const result = filterFramesByTimeRange(frames, 20, 20);
    expect(result).toHaveLength(1);
    expect(result[0].timestamp_ms).toBe(20);
  });

  it("handles empty input array", () => {
    expect(filterFramesByTimeRange([], 0, 100)).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Data transformation edge cases (Step 19)
// ---------------------------------------------------------------------------

describe("Data transformation edge cases", () => {
  it("handles session with 0 frames (empty frames array)", () => {
    const frames: Frame[] = [];
    expect(filterThermalFrames(frames)).toEqual([]);
    expect(filterFramesByTimeRange(frames, null, null)).toEqual([]);
    expect(filterFramesByTimeRange(frames, 0, 10000)).toEqual([]);
  });

  it("handles empty thermal_snapshots in frame", () => {
    const frame = makeThermalFrame({
      thermal_snapshots: [],
      has_thermal_data: false,
    });
    expect(extractCenterTemperature(frame)).toBeNull();
    expect(extractAllTemperatures(frame)).toEqual([]);
  });

  it("filterThermalFrames returns only frames with thermal_snapshots.length > 0", () => {
    const thermalFrame = makeThermalFrame({ timestamp_ms: 100 });
    const sensorFrame = makeSensorOnlyFrame({ timestamp_ms: 10 });
    const result = filterThermalFrames([sensorFrame, thermalFrame, sensorFrame]);
    expect(result).toHaveLength(1);
    expect(result[0].timestamp_ms).toBe(100);
    expect(result[0].has_thermal_data).toBe(true);
  });
});
