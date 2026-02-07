/**
 * Session type definition for the canonical time-series contract.
 *
 * Mirrors the backend Pydantic model in `backend/models/session.py` exactly.
 * Field names use snake_case — no conversion layer between backend and frontend.
 *
 * A Session is the top-level container for a welding recording. It holds:
 *   - Identity & audit metadata (session_id, operator_id, start_time, weld_type)
 *   - Sensor configuration (sample rates, thermal directions/intervals)
 *   - Ordered frame list (the actual time-series data)
 *   - Ingestion status tracking (status, frame_count, validation_errors, etc.)
 *
 * The backend enforces heavy validation on this model (timestamp ordering,
 * thermal distance consistency, sensor continuity). The frontend mirrors
 * the shape and provides lightweight runtime guards.
 */

import type { Frame } from "./frame";

// ---------------------------------------------------------------------------
// SessionStatus
// ---------------------------------------------------------------------------

/**
 * Session lifecycle status.
 *
 * Mirrors `backend/models/session.py → SessionStatus` enum.
 *
 * Valid transitions:
 * ```
 * RECORDING → INCOMPLETE | COMPLETE | FAILED
 * INCOMPLETE → RECORDING | FAILED | ARCHIVED
 * COMPLETE → ARCHIVED
 * FAILED → ARCHIVED
 * ARCHIVED → (terminal, no transitions)
 * ```
 */
export type SessionStatus =
  | "recording"
  | "incomplete"
  | "complete"
  | "failed"
  | "archived";

/**
 * All valid session statuses as a readonly array.
 * Useful for iteration, dropdowns, and runtime validation.
 */
export const SESSION_STATUSES: readonly SessionStatus[] = [
  "recording",
  "incomplete",
  "complete",
  "failed",
  "archived",
] as const;

/**
 * Allowed status transitions, mirroring the backend `is_valid_status_transition`.
 * Key = current status, Value = set of statuses it can transition to.
 */
export const VALID_STATUS_TRANSITIONS: Readonly<
  Record<SessionStatus, readonly SessionStatus[]>
> = {
  recording: ["incomplete", "complete", "failed"],
  incomplete: ["recording", "failed", "archived"],
  complete: ["archived"],
  failed: ["archived"],
  archived: [],
} as const;

/**
 * Check whether a status transition is valid.
 *
 * Mirrors `backend/models/session.py → Session.is_valid_status_transition`.
 * Same-status transitions are always allowed (no-op).
 *
 * @param previous - The current status.
 * @param next - The desired new status.
 * @returns `true` if the transition is allowed.
 */
export function isValidStatusTransition(
  previous: SessionStatus,
  next: SessionStatus
): boolean {
  if (previous === next) return true;
  return (VALID_STATUS_TRANSITIONS[previous] as readonly string[]).includes(
    next
  );
}

// ---------------------------------------------------------------------------
// Session
// ---------------------------------------------------------------------------

/**
 * Complete welding session with canonical time-series frames.
 *
 * Mirrors `backend/models/session.py → Session`.
 *
 * @example
 * ```typescript
 * const session: Session = {
 *   session_id: "sess_001",
 *   operator_id: "op_42",
 *   start_time: "2026-02-07T10:00:00Z",
 *   weld_type: "butt_joint",
 *   thermal_sample_interval_ms: 100,
 *   thermal_directions: ["center", "north", "south", "east", "west"],
 *   thermal_distance_interval_mm: 10.0,
 *   sensor_sample_rate_hz: 100,
 *   frames: [],
 *   status: "recording",
 *   frame_count: 0,
 *   expected_frame_count: null,
 *   last_successful_frame_index: null,
 *   validation_errors: [],
 *   completed_at: null,
 * };
 * ```
 */
export interface Session {
  // -------------------------------------------------------------------------
  // Identity & audit metadata
  // -------------------------------------------------------------------------

  /** Unique session identifier (e.g. "sess_001"). */
  session_id: string;

  /** Operator identifier for audit trail (e.g. "op_42"). */
  operator_id: string;

  /**
   * Session start time as ISO 8601 string.
   *
   * The backend sends `datetime` serialized to ISO 8601.
   * Parse with `new Date(session.start_time)` when needed.
   */
  start_time: string;

  /** Weld type identifier (e.g. "butt_joint", "fillet"). */
  weld_type: string;

  // -------------------------------------------------------------------------
  // Sensor configuration
  // -------------------------------------------------------------------------

  /**
   * Thermal sampling interval in milliseconds.
   * Must be > 0. Typical value: 100 (= 5Hz thermal sampling within 100Hz frames).
   */
  thermal_sample_interval_ms: number;

  /**
   * Ordered thermal directions measured per snapshot.
   * Typical: ["center", "north", "south", "east", "west"].
   * Must have at least 1 element.
   */
  thermal_directions: string[];

  /**
   * Expected distance interval between thermal snapshots in millimeters.
   * Must be > 0. Used by the backend to validate distance consistency.
   */
  thermal_distance_interval_mm: number;

  /**
   * Sensor sampling rate in Hertz.
   * Must be > 0. Typical value: 100 (= 10ms frame interval).
   */
  sensor_sample_rate_hz: number;

  // -------------------------------------------------------------------------
  // Frame data
  // -------------------------------------------------------------------------

  /**
   * Ordered list of sensor frames.
   *
   * Backend invariants:
   *   - Timestamps are unique and sequential (~10ms apart).
   *   - Thermal distances are consistent across all frames.
   *   - Sensor values don't jump >20% amps / >10% volts between frames.
   *
   * WARNING: May contain up to 30,000 frames (5 min session).
   * Use pagination (limit/offset) or streaming for large sessions.
   */
  frames: Frame[];

  // -------------------------------------------------------------------------
  // Ingestion status tracking
  // -------------------------------------------------------------------------

  /**
   * Current session lifecycle status.
   * See `SessionStatus` type and `VALID_STATUS_TRANSITIONS` for allowed transitions.
   */
  status: SessionStatus;

  /**
   * Total number of frames ingested so far.
   *
   * Backend invariant: must equal `frames.length`.
   */
  frame_count: number;

  /**
   * Expected total frame count for the session.
   *
   * `null` while recording (unknown until session ends).
   * Required when `status === "complete"`.
   */
  expected_frame_count: number | null;

  /**
   * Index (0-based) of the last successfully ingested frame.
   *
   * `null` if no frames have been ingested yet.
   * When `status === "complete"`, must equal `frame_count - 1`.
   */
  last_successful_frame_index: number | null;

  /**
   * Validation errors collected during ingestion.
   *
   * Empty array means no errors. Non-empty means the session
   * encountered issues but ingestion continued (best-effort).
   */
  validation_errors: string[];

  /**
   * Completion timestamp as ISO 8601 string.
   *
   * `null` unless `status === "complete"`.
   * Required when status is "complete".
   */
  completed_at: string | null;
}

// ---------------------------------------------------------------------------
// Runtime validation
// ---------------------------------------------------------------------------

/**
 * Validate that a `Session` satisfies the canonical contract at runtime.
 *
 * Checks performed:
 *   1. Required string fields are non-empty.
 *   2. Numeric configuration fields are positive.
 *   3. `thermal_directions` has at least 1 element.
 *   4. `status` is a valid `SessionStatus`.
 *   5. `frame_count` matches `frames.length`.
 *   6. Completion invariants when `status === "complete"`.
 *   7. `start_time` is a parseable ISO 8601 date.
 *
 * NOTE: This does NOT validate individual frames (use `validateFrame` for that)
 * or cross-frame invariants (timestamp ordering, sensor continuity) — those
 * are enforced by the backend.
 *
 * @param session - The session to validate.
 * @returns An array of error messages (empty if valid).
 */
export function validateSession(session: Session): string[] {
  const errors: string[] = [];

  // 1. Required string fields non-empty
  if (!session.session_id) {
    errors.push("session_id is required and must be non-empty");
  }
  if (!session.operator_id) {
    errors.push("operator_id is required and must be non-empty");
  }
  if (!session.weld_type) {
    errors.push("weld_type is required and must be non-empty");
  }

  // 7. start_time parseable
  if (!session.start_time) {
    errors.push("start_time is required and must be non-empty");
  } else {
    const parsed = new Date(session.start_time);
    if (isNaN(parsed.getTime())) {
      errors.push(
        `start_time must be a valid ISO 8601 date, got "${session.start_time}"`
      );
    }
  }

  // 2. Numeric configuration fields > 0
  if (
    typeof session.thermal_sample_interval_ms !== "number" ||
    session.thermal_sample_interval_ms <= 0
  ) {
    errors.push(
      `thermal_sample_interval_ms must be > 0, got ${session.thermal_sample_interval_ms}`
    );
  }
  if (
    typeof session.thermal_distance_interval_mm !== "number" ||
    session.thermal_distance_interval_mm <= 0
  ) {
    errors.push(
      `thermal_distance_interval_mm must be > 0, got ${session.thermal_distance_interval_mm}`
    );
  }
  if (
    typeof session.sensor_sample_rate_hz !== "number" ||
    session.sensor_sample_rate_hz <= 0
  ) {
    errors.push(
      `sensor_sample_rate_hz must be > 0, got ${session.sensor_sample_rate_hz}`
    );
  }

  // 3. thermal_directions has at least 1 element
  if (
    !Array.isArray(session.thermal_directions) ||
    session.thermal_directions.length === 0
  ) {
    errors.push("thermal_directions must have at least 1 element");
  }

  // 4. status is valid
  if (!(SESSION_STATUSES as readonly string[]).includes(session.status)) {
    errors.push(`Invalid status: "${session.status}"`);
  }

  // 5. frame_count matches frames.length
  if (session.frame_count !== session.frames.length) {
    errors.push(
      `frame_count (${session.frame_count}) does not match frames.length (${session.frames.length})`
    );
  }

  // 6. Completion invariants
  if (session.status === "complete") {
    if (session.expected_frame_count === null) {
      errors.push(
        "expected_frame_count is required when status is 'complete'"
      );
    } else if (session.frame_count !== session.expected_frame_count) {
      errors.push(
        `frame_count (${session.frame_count}) must equal expected_frame_count ` +
          `(${session.expected_frame_count}) when status is 'complete'`
      );
    }
    if (
      session.last_successful_frame_index === null ||
      session.last_successful_frame_index !== session.frame_count - 1
    ) {
      errors.push(
        "last_successful_frame_index must equal frame_count - 1 when status is 'complete'"
      );
    }
    if (!session.completed_at) {
      errors.push("completed_at is required when status is 'complete'");
    }
  }

  return errors;
}
