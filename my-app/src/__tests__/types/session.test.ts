/**
 * Tests for frontend Session type (Step 11).
 *
 * Validates:
 *   - SessionStatus type and SESSION_STATUSES constant
 *   - Status transition logic (isValidStatusTransition)
 *   - Session interface structure and snake_case naming
 *   - validateSession() runtime checks
 *   - Completion invariants (status === "complete")
 *   - Edge cases: empty sessions, missing fields, invalid config
 */

import type { Frame } from "@/types/frame";
import type { Session, SessionStatus } from "@/types/session";
import {
  SESSION_STATUSES,
  VALID_STATUS_TRANSITIONS,
  isValidStatusTransition,
  validateSession,
} from "@/types/session";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a valid sensor-only frame at a given timestamp. */
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

/** Build a valid recording session with no frames. */
function makeEmptySession(overrides: Partial<Session> = {}): Session {
  return {
    session_id: "sess_001",
    operator_id: "op_42",
    start_time: "2026-02-07T10:00:00Z",
    weld_type: "butt_joint",
    thermal_sample_interval_ms: 100,
    thermal_directions: ["center", "north", "south", "east", "west"],
    thermal_distance_interval_mm: 10.0,
    sensor_sample_rate_hz: 100,
    frames: [],
    status: "recording",
    frame_count: 0,
    expected_frame_count: null,
    last_successful_frame_index: null,
    validation_errors: [],
    completed_at: null,
    ...overrides,
  };
}

/** Build a valid complete session with 3 frames. */
function makeCompleteSession(overrides: Partial<Session> = {}): Session {
  const frames = [makeFrame(0), makeFrame(10), makeFrame(20)];
  return {
    session_id: "sess_002",
    operator_id: "op_42",
    start_time: "2026-02-07T10:00:00Z",
    weld_type: "fillet",
    thermal_sample_interval_ms: 100,
    thermal_directions: ["center", "north", "south", "east", "west"],
    thermal_distance_interval_mm: 10.0,
    sensor_sample_rate_hz: 100,
    frames,
    status: "complete",
    frame_count: 3,
    expected_frame_count: 3,
    last_successful_frame_index: 2,
    validation_errors: [],
    completed_at: "2026-02-07T10:00:01Z",
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// SESSION_STATUSES constant
// ---------------------------------------------------------------------------

describe("SESSION_STATUSES constant", () => {
  it("has exactly 5 statuses", () => {
    expect(SESSION_STATUSES).toHaveLength(5);
  });

  it("contains all lifecycle statuses", () => {
    expect(SESSION_STATUSES).toContain("recording");
    expect(SESSION_STATUSES).toContain("incomplete");
    expect(SESSION_STATUSES).toContain("complete");
    expect(SESSION_STATUSES).toContain("failed");
    expect(SESSION_STATUSES).toContain("archived");
  });
});

// ---------------------------------------------------------------------------
// VALID_STATUS_TRANSITIONS
// ---------------------------------------------------------------------------

describe("VALID_STATUS_TRANSITIONS constant", () => {
  it("recording can go to incomplete, complete, or failed", () => {
    expect(VALID_STATUS_TRANSITIONS.recording).toEqual(
      expect.arrayContaining(["incomplete", "complete", "failed"])
    );
    expect(VALID_STATUS_TRANSITIONS.recording).toHaveLength(3);
  });

  it("incomplete can go to recording, failed, or archived", () => {
    expect(VALID_STATUS_TRANSITIONS.incomplete).toEqual(
      expect.arrayContaining(["recording", "failed", "archived"])
    );
    expect(VALID_STATUS_TRANSITIONS.incomplete).toHaveLength(3);
  });

  it("complete can only go to archived", () => {
    expect(VALID_STATUS_TRANSITIONS.complete).toEqual(["archived"]);
  });

  it("failed can only go to archived", () => {
    expect(VALID_STATUS_TRANSITIONS.failed).toEqual(["archived"]);
  });

  it("archived is terminal (no transitions)", () => {
    expect(VALID_STATUS_TRANSITIONS.archived).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// isValidStatusTransition
// ---------------------------------------------------------------------------

describe("isValidStatusTransition", () => {
  it("same-status transition is always valid (no-op)", () => {
    for (const status of SESSION_STATUSES) {
      expect(isValidStatusTransition(status, status)).toBe(true);
    }
  });

  it("recording → complete is valid", () => {
    expect(isValidStatusTransition("recording", "complete")).toBe(true);
  });

  it("recording → incomplete is valid", () => {
    expect(isValidStatusTransition("recording", "incomplete")).toBe(true);
  });

  it("recording → failed is valid", () => {
    expect(isValidStatusTransition("recording", "failed")).toBe(true);
  });

  it("recording → archived is NOT valid", () => {
    expect(isValidStatusTransition("recording", "archived")).toBe(false);
  });

  it("complete → recording is NOT valid", () => {
    expect(isValidStatusTransition("complete", "recording")).toBe(false);
  });

  it("complete → archived is valid", () => {
    expect(isValidStatusTransition("complete", "archived")).toBe(true);
  });

  it("archived → anything is NOT valid (terminal)", () => {
    expect(isValidStatusTransition("archived", "recording")).toBe(false);
    expect(isValidStatusTransition("archived", "incomplete")).toBe(false);
    expect(isValidStatusTransition("archived", "complete")).toBe(false);
    expect(isValidStatusTransition("archived", "failed")).toBe(false);
  });

  it("incomplete → recording is valid (resume)", () => {
    expect(isValidStatusTransition("incomplete", "recording")).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Session interface — snake_case naming
// ---------------------------------------------------------------------------

describe("Session interface — snake_case field names", () => {
  it("has all expected keys", () => {
    const session = makeEmptySession();
    const keys = Object.keys(session);
    expect(keys).toContain("session_id");
    expect(keys).toContain("operator_id");
    expect(keys).toContain("start_time");
    expect(keys).toContain("weld_type");
    expect(keys).toContain("thermal_sample_interval_ms");
    expect(keys).toContain("thermal_directions");
    expect(keys).toContain("thermal_distance_interval_mm");
    expect(keys).toContain("sensor_sample_rate_hz");
    expect(keys).toContain("frames");
    expect(keys).toContain("status");
    expect(keys).toContain("frame_count");
    expect(keys).toContain("expected_frame_count");
    expect(keys).toContain("last_successful_frame_index");
    expect(keys).toContain("validation_errors");
    expect(keys).toContain("completed_at");
  });

  it("no camelCase keys exist", () => {
    const session = makeEmptySession();
    const keys = Object.keys(session);
    expect(keys).not.toContain("sessionId");
    expect(keys).not.toContain("operatorId");
    expect(keys).not.toContain("startTime");
    expect(keys).not.toContain("weldType");
    expect(keys).not.toContain("thermalSampleIntervalMs");
    expect(keys).not.toContain("frameCount");
    expect(keys).not.toContain("completedAt");
  });
});

// ---------------------------------------------------------------------------
// validateSession — valid sessions
// ---------------------------------------------------------------------------

describe("validateSession — valid sessions", () => {
  it("returns no errors for a valid empty recording session", () => {
    const errors = validateSession(makeEmptySession());
    expect(errors).toEqual([]);
  });

  it("returns no errors for a valid complete session", () => {
    const errors = validateSession(makeCompleteSession());
    expect(errors).toEqual([]);
  });

  it("returns no errors for an incomplete session", () => {
    const session = makeEmptySession({
      status: "incomplete",
      frames: [makeFrame(0)],
      frame_count: 1,
      last_successful_frame_index: 0,
    });
    const errors = validateSession(session);
    expect(errors).toEqual([]);
  });

  it("returns no errors for a failed session with validation errors", () => {
    const session = makeEmptySession({
      status: "failed",
      validation_errors: ["Sensor disconnected at frame 500"],
    });
    const errors = validateSession(session);
    expect(errors).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// validateSession — required string fields
// ---------------------------------------------------------------------------

describe("validateSession — required string fields", () => {
  it("rejects empty session_id", () => {
    const session = makeEmptySession({ session_id: "" });
    const errors = validateSession(session);
    expect(errors.some((e) => e.includes("session_id"))).toBe(true);
  });

  it("rejects empty operator_id", () => {
    const session = makeEmptySession({ operator_id: "" });
    const errors = validateSession(session);
    expect(errors.some((e) => e.includes("operator_id"))).toBe(true);
  });

  it("rejects empty weld_type", () => {
    const session = makeEmptySession({ weld_type: "" });
    const errors = validateSession(session);
    expect(errors.some((e) => e.includes("weld_type"))).toBe(true);
  });

  it("rejects empty start_time", () => {
    const session = makeEmptySession({ start_time: "" });
    const errors = validateSession(session);
    expect(errors.some((e) => e.includes("start_time"))).toBe(true);
  });

  it("rejects unparseable start_time", () => {
    const session = makeEmptySession({ start_time: "not-a-date" });
    const errors = validateSession(session);
    expect(errors.some((e) => e.includes("valid ISO 8601"))).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// validateSession — numeric configuration fields
// ---------------------------------------------------------------------------

describe("validateSession — numeric configuration fields", () => {
  it("rejects thermal_sample_interval_ms <= 0", () => {
    const session = makeEmptySession({ thermal_sample_interval_ms: 0 });
    const errors = validateSession(session);
    expect(
      errors.some((e) => e.includes("thermal_sample_interval_ms must be > 0"))
    ).toBe(true);
  });

  it("rejects thermal_distance_interval_mm <= 0", () => {
    const session = makeEmptySession({ thermal_distance_interval_mm: -1 });
    const errors = validateSession(session);
    expect(
      errors.some((e) => e.includes("thermal_distance_interval_mm must be > 0"))
    ).toBe(true);
  });

  it("rejects sensor_sample_rate_hz <= 0", () => {
    const session = makeEmptySession({ sensor_sample_rate_hz: 0 });
    const errors = validateSession(session);
    expect(
      errors.some((e) => e.includes("sensor_sample_rate_hz must be > 0"))
    ).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// validateSession — thermal_directions
// ---------------------------------------------------------------------------

describe("validateSession — thermal_directions", () => {
  it("rejects empty thermal_directions array", () => {
    const session = makeEmptySession({ thermal_directions: [] });
    const errors = validateSession(session);
    expect(
      errors.some((e) => e.includes("thermal_directions must have at least 1"))
    ).toBe(true);
  });

  it("accepts single-element thermal_directions", () => {
    const session = makeEmptySession({ thermal_directions: ["center"] });
    const errors = validateSession(session);
    expect(errors).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// validateSession — status validation
// ---------------------------------------------------------------------------

describe("validateSession — status validation", () => {
  it("accepts all valid statuses", () => {
    for (const status of SESSION_STATUSES) {
      const session = makeEmptySession({ status });
      const errors = validateSession(session);
      // May have completion errors for "complete", but not invalid status
      expect(errors.some((e) => e.includes("Invalid status"))).toBe(false);
    }
  });

  it("rejects invalid status string", () => {
    const session = makeEmptySession({
      status: "paused" as SessionStatus,
    });
    const errors = validateSession(session);
    expect(errors.some((e) => e.includes('Invalid status: "paused"'))).toBe(
      true
    );
  });
});

// ---------------------------------------------------------------------------
// validateSession — frame_count consistency
// ---------------------------------------------------------------------------

describe("validateSession — frame_count consistency", () => {
  it("rejects frame_count mismatch with frames.length", () => {
    const session = makeEmptySession({
      frames: [makeFrame(0)],
      frame_count: 0, // mismatch: 0 vs 1
    });
    const errors = validateSession(session);
    expect(errors.some((e) => e.includes("does not match frames.length"))).toBe(
      true
    );
  });

  it("accepts matching frame_count and frames.length", () => {
    const session = makeEmptySession({
      frames: [makeFrame(0), makeFrame(10)],
      frame_count: 2,
    });
    const errors = validateSession(session);
    expect(errors).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// validateSession — completion invariants
// ---------------------------------------------------------------------------

describe("validateSession — completion invariants", () => {
  it("rejects complete session without expected_frame_count", () => {
    const session = makeCompleteSession({ expected_frame_count: null });
    const errors = validateSession(session);
    expect(
      errors.some((e) => e.includes("expected_frame_count is required"))
    ).toBe(true);
  });

  it("rejects complete session where frame_count != expected_frame_count", () => {
    const session = makeCompleteSession({ expected_frame_count: 999 });
    const errors = validateSession(session);
    expect(
      errors.some((e) => e.includes("must equal expected_frame_count"))
    ).toBe(true);
  });

  it("rejects complete session with wrong last_successful_frame_index", () => {
    const session = makeCompleteSession({
      last_successful_frame_index: 0, // should be 2 (frame_count - 1)
    });
    const errors = validateSession(session);
    expect(
      errors.some((e) =>
        e.includes("last_successful_frame_index must equal frame_count - 1")
      )
    ).toBe(true);
  });

  it("rejects complete session without completed_at", () => {
    const session = makeCompleteSession({ completed_at: null });
    const errors = validateSession(session);
    expect(errors.some((e) => e.includes("completed_at is required"))).toBe(
      true
    );
  });

  it("does NOT enforce completion invariants on non-complete statuses", () => {
    // A recording session with null expected_frame_count is fine
    const session = makeEmptySession({
      status: "recording",
      expected_frame_count: null,
      completed_at: null,
    });
    const errors = validateSession(session);
    expect(errors).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Old WeldingSession removal
// ---------------------------------------------------------------------------

describe("WeldingSession removal", () => {
  it("session.ts no longer exports WeldingSession", async () => {
    // Dynamic import to check exports
    const sessionModule = await import("@/types/session");
    expect("WeldingSession" in sessionModule).toBe(false);
  });

  it("session.ts exports Session interface (verified via validateSession)", async () => {
    const sessionModule = await import("@/types/session");
    expect(typeof sessionModule.validateSession).toBe("function");
    expect(typeof sessionModule.isValidStatusTransition).toBe("function");
    expect(Array.isArray(sessionModule.SESSION_STATUSES)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Type-level compile-time checks
// ---------------------------------------------------------------------------

describe("Type-level compile-time safety", () => {
  it("Session requires all mandatory fields", () => {
    // Documents the full shape. If a field is removed, this fails to compile.
    const session: Session = makeEmptySession();
    const keys = Object.keys(session);
    // 15 fields total
    expect(keys).toHaveLength(15);
  });

  it("SessionStatus only accepts valid string literals", () => {
    const s1: SessionStatus = "recording";
    const s2: SessionStatus = "incomplete";
    const s3: SessionStatus = "complete";
    const s4: SessionStatus = "failed";
    const s5: SessionStatus = "archived";
    expect([s1, s2, s3, s4, s5]).toHaveLength(5);
  });
});
