/**
 * Step 18: Frontend serialization tests (JSON → TypeScript).
 *
 * Verifies that JSON from the backend API (snake_case, ISO 8601 datetimes,
 * SessionStatus strings) parses correctly and passes frontend validation.
 *
 * Backend uses Pydantic model_dump(mode="json"); frontend consumes via fetch → JSON.parse.
 */

import type { Frame } from "@/types/frame";
import type { Session, SessionStatus } from "@/types/session";
import type { ThermalSnapshot } from "@/types/thermal";
import { validateFrame } from "@/types/frame";
import { SESSION_STATUSES, validateSession } from "@/types/session";
import { validateThermalSnapshot } from "@/types/thermal";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Valid 5-reading thermal snapshot in backend JSON shape. */
function makeReadingsJson(baseTemp: number = 400.0) {
  return [
    { direction: "center", temp_celsius: baseTemp },
    { direction: "north", temp_celsius: baseTemp - 10 },
    { direction: "south", temp_celsius: baseTemp - 20 },
    { direction: "east", temp_celsius: baseTemp - 15 },
    { direction: "west", temp_celsius: baseTemp - 25 },
  ];
}

// ---------------------------------------------------------------------------
// Round-trip: JSON string → parse → validate (simulates API → frontend)
// ---------------------------------------------------------------------------

describe("Serialization — JSON parse and validate", () => {
  it("parses minimal Session JSON and passes validation", () => {
    const json = JSON.stringify({
      session_id: "sess_ser_001",
      operator_id: "op_01",
      start_time: "2026-02-07T10:00:00Z",
      weld_type: "mild_steel",
      thermal_sample_interval_ms: 100,
      thermal_directions: ["center", "north", "south", "east", "west"],
      thermal_distance_interval_mm: 10.0,
      sensor_sample_rate_hz: 100,
      frames: [],
      frame_count: 0,
      status: "recording",
      expected_frame_count: null,
      last_successful_frame_index: null,
      validation_errors: [],
      completed_at: null,
    });
    const parsed = JSON.parse(json) as Session;
    expect(validateSession(parsed)).toEqual([]);
    expect(parsed.session_id).toBe("sess_ser_001");
    expect(parsed.status).toBe("recording");
  });

  it("parses Frame JSON with thermal data and passes validation", () => {
    const frameJson = {
      timestamp_ms: 100,
      volts: 22.5,
      amps: 150.0,
      angle_degrees: 45.0,
      thermal_snapshots: [
        {
          distance_mm: 10.0,
          readings: makeReadingsJson(425.0),
        },
      ],
      has_thermal_data: true,
      optional_sensors: null,
      heat_dissipation_rate_celsius_per_sec: -5.2,
    };
    const parsed = JSON.parse(JSON.stringify(frameJson)) as Frame;
    expect(validateFrame(parsed)).toEqual([]);
    expect(parsed.thermal_snapshots[0].distance_mm).toBe(10.0);
    expect(parsed.thermal_snapshots[0].readings).toHaveLength(5);
  });

  it("parses ThermalSnapshot JSON and passes validation", () => {
    const snapshotJson = {
      distance_mm: 10.0,
      readings: makeReadingsJson(425.3),
    };
    const parsed = JSON.parse(JSON.stringify(snapshotJson)) as ThermalSnapshot;
    expect(validateThermalSnapshot(parsed)).toEqual([]);
    expect(parsed.distance_mm).toBe(10.0);
    const center = parsed.readings.find((r) => r.direction === "center");
    expect(center?.temp_celsius).toBe(425.3);
  });
});

// ---------------------------------------------------------------------------
// Snake_case — parsed JSON must have snake_case keys (no camelCase)
// ---------------------------------------------------------------------------

describe("Serialization — snake_case field names", () => {
  it("parsed Session has snake_case keys", () => {
    const json = JSON.stringify({
      session_id: "s1",
      operator_id: "o1",
      start_time: "2026-02-07T10:00:00Z",
      weld_type: "mild_steel",
      thermal_sample_interval_ms: 100,
      thermal_directions: ["center"],
      thermal_distance_interval_mm: 10.0,
      sensor_sample_rate_hz: 100,
      frames: [],
      frame_count: 0,
      status: "recording",
      expected_frame_count: null,
      last_successful_frame_index: null,
      validation_errors: [],
      completed_at: null,
    });
    const parsed = JSON.parse(json) as Session;
    expect(parsed).toHaveProperty("session_id");
    expect(parsed).toHaveProperty("thermal_sample_interval_ms");
    expect(parsed).not.toHaveProperty("sessionId");
    expect(parsed).not.toHaveProperty("thermalSampleIntervalMs");
  });

  it("parsed Frame has snake_case keys", () => {
    const frameJson = {
      timestamp_ms: 0,
      volts: 22.5,
      amps: 150.0,
      angle_degrees: 45.0,
      thermal_snapshots: [],
      has_thermal_data: false,
      optional_sensors: null,
      heat_dissipation_rate_celsius_per_sec: null,
    };
    const parsed = JSON.parse(JSON.stringify(frameJson)) as Frame;
    expect(parsed).toHaveProperty("timestamp_ms");
    expect(parsed).toHaveProperty("angle_degrees");
    expect(parsed).toHaveProperty("heat_dissipation_rate_celsius_per_sec");
    expect(parsed).not.toHaveProperty("timestampMs");
    expect(parsed).not.toHaveProperty("angleDegrees");
  });
});

// ---------------------------------------------------------------------------
// Extreme float values — JSON preserves double precision
// ---------------------------------------------------------------------------

describe("Serialization — extreme float values", () => {
  it("extreme volts/amps survive JSON round-trip", () => {
    const frameJson = {
      timestamp_ms: 0,
      volts: 22.123456789012345,
      amps: 150.987654321,
      angle_degrees: 45.0,
      thermal_snapshots: [],
      has_thermal_data: false,
      optional_sensors: null,
      heat_dissipation_rate_celsius_per_sec: null,
    };
    const json = JSON.stringify(frameJson);
    const parsed = JSON.parse(json) as Frame;
    expect(parsed.volts).toBe(22.123456789012345);
    expect(parsed.amps).toBe(150.987654321);
  });

  it("extreme temp_celsius survives JSON round-trip", () => {
    const readings = makeReadingsJson(9999.123456789);
    const snapshotJson = { distance_mm: 10.0, readings };
    const json = JSON.stringify(snapshotJson);
    const parsed = JSON.parse(json) as ThermalSnapshot;
    const center = parsed.readings.find((r) => r.direction === "center");
    expect(center?.temp_celsius).toBe(9999.123456789);
  });

  it("negative heat_dissipation survives JSON round-trip", () => {
    const frameJson = {
      timestamp_ms: 0,
      thermal_snapshots: [],
      has_thermal_data: false,
      optional_sensors: null,
      heat_dissipation_rate_celsius_per_sec: -500.987654,
    };
    const parsed = JSON.parse(JSON.stringify(frameJson)) as Frame;
    expect(parsed.heat_dissipation_rate_celsius_per_sec).toBe(-500.987654);
  });
});

// ---------------------------------------------------------------------------
// Null handling — optional fields as null
// ---------------------------------------------------------------------------

describe("Serialization — null handling", () => {
  it("optional_sensors: null parses correctly", () => {
    const frameJson = {
      timestamp_ms: 0,
      volts: null,
      amps: null,
      angle_degrees: null,
      thermal_snapshots: [],
      has_thermal_data: false,
      optional_sensors: null,
      heat_dissipation_rate_celsius_per_sec: null,
    };
    const parsed = JSON.parse(JSON.stringify(frameJson)) as Frame;
    expect(parsed.optional_sensors).toBeNull();
    expect(validateFrame(parsed)).toEqual([]);
  });

  it("heat_dissipation_rate_celsius_per_sec: null parses correctly", () => {
    const frameJson = {
      timestamp_ms: 0,
      thermal_snapshots: [],
      has_thermal_data: false,
      optional_sensors: null,
      heat_dissipation_rate_celsius_per_sec: null,
    };
    const parsed = JSON.parse(JSON.stringify(frameJson)) as Frame;
    expect(parsed.heat_dissipation_rate_celsius_per_sec).toBeNull();
  });

  it("thermal_snapshots: [] parses as empty array", () => {
    const frameJson = {
      timestamp_ms: 0,
      thermal_snapshots: [],
      has_thermal_data: false,
      optional_sensors: null,
      heat_dissipation_rate_celsius_per_sec: null,
    };
    const parsed = JSON.parse(JSON.stringify(frameJson)) as Frame;
    expect(parsed.thermal_snapshots).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Datetime ISO 8601
// ---------------------------------------------------------------------------

describe("Serialization — datetime ISO 8601", () => {
  it("start_time as ISO 8601 string parses and validates", () => {
    const session = {
      session_id: "s1",
      operator_id: "o1",
      start_time: "2026-02-07T10:00:00.000Z",
      weld_type: "mild_steel",
      thermal_sample_interval_ms: 100,
      thermal_directions: ["center"],
      thermal_distance_interval_mm: 10.0,
      sensor_sample_rate_hz: 100,
      frames: [],
      frame_count: 0,
      status: "recording",
      expected_frame_count: null,
      last_successful_frame_index: null,
      validation_errors: [],
      completed_at: null,
    };
    const parsed = JSON.parse(JSON.stringify(session)) as Session;
    expect(parsed.start_time).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    const date = new Date(parsed.start_time);
    expect(date.getUTCFullYear()).toBe(2026);
    expect(date.getUTCMonth()).toBe(1); // February = 1
    expect(validateSession(parsed)).toEqual([]);
  });

  it("completed_at as ISO 8601 string parses correctly", () => {
    const session = {
      session_id: "s1",
      operator_id: "o1",
      start_time: "2026-02-07T10:00:00Z",
      weld_type: "mild_steel",
      thermal_sample_interval_ms: 100,
      thermal_directions: ["center"],
      thermal_distance_interval_mm: 10.0,
      sensor_sample_rate_hz: 100,
      frames: [{ timestamp_ms: 0, thermal_snapshots: [], has_thermal_data: false, optional_sensors: null, heat_dissipation_rate_celsius_per_sec: null }],
      frame_count: 1,
      status: "complete",
      expected_frame_count: 1,
      last_successful_frame_index: 0,
      validation_errors: [],
      completed_at: "2026-02-07T10:01:30.000Z",
    };
    const parsed = JSON.parse(JSON.stringify(session)) as Session;
    expect(parsed.completed_at).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    const date = new Date(parsed.completed_at!);
    expect(date.getUTCMinutes()).toBe(1);
    expect(date.getUTCSeconds()).toBe(30);
  });
});

// ---------------------------------------------------------------------------
// SessionStatus string serialization
// ---------------------------------------------------------------------------

describe("Serialization — SessionStatus string values", () => {
  it("all SESSION_STATUSES string values parse and validate", () => {
    for (const status of SESSION_STATUSES) {
      const session = {
        session_id: "s1",
        operator_id: "o1",
        start_time: "2026-02-07T10:00:00Z",
        weld_type: "mild_steel",
        thermal_sample_interval_ms: 100,
        thermal_directions: ["center"],
        thermal_distance_interval_mm: 10.0,
        sensor_sample_rate_hz: 100,
        frames: [],
        frame_count: 0,
        status,
        expected_frame_count: null,
        last_successful_frame_index: null,
        validation_errors: [],
        completed_at: null,
      };
      const parsed = JSON.parse(JSON.stringify(session)) as Session;
      expect(parsed.status).toBe(status);
      // Only "complete" may fail due to completion invariants
      const errors = validateSession(parsed);
      expect(errors.some((e) => e.includes("Invalid status"))).toBe(false);
    }
  });

  it("status value is a string (not enum number)", () => {
    const session = JSON.parse(
      JSON.stringify({
        session_id: "s1",
        operator_id: "o1",
        start_time: "2026-02-07T10:00:00Z",
        weld_type: "mild_steel",
        thermal_sample_interval_ms: 100,
        thermal_directions: ["center"],
        thermal_distance_interval_mm: 10.0,
        sensor_sample_rate_hz: 100,
        frames: [],
        frame_count: 0,
        status: "recording",
        expected_frame_count: null,
        last_successful_frame_index: null,
        validation_errors: [],
        completed_at: null,
      })
    ) as Session;
    expect(typeof session.status).toBe("string");
    expect(session.status as SessionStatus).toBe("recording");
  });
});
