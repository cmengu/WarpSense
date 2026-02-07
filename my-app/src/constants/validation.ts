/**
 * Any change here can ripple through components, services, tests, and occasionally the backend.
 * Validation constants for the canonical time-series contract.
 *
 * These values must match the backend validation rules exactly.
 * If the backend changes a threshold, update it here too.
 *
 * Source of truth: backend/models/session.py, backend/models/frame.py,
 * backend/models/thermal.py, backend/routes/sessions.py.
 */

// ---------------------------------------------------------------------------
// Frame timing
// ---------------------------------------------------------------------------

/**
 * Expected interval between consecutive frames in milliseconds.
 * Matches backend: 100Hz sampling = 10ms per frame.
 */
export const FRAME_INTERVAL_MS = 10;

/**
 * Tolerance for frame interval validation in milliseconds.
 * Backend allows ±1ms to account for floating point / hardware jitter.
 */
export const FRAME_INTERVAL_TOLERANCE_MS = 1;

/**
 * Thermal sampling interval in milliseconds.
 * Thermal snapshots appear every 100ms (every 10th frame at 100Hz).
 * Note: this is the typical value; actual value is per-session config.
 */
export const THERMAL_SAMPLE_INTERVAL_MS = 100;

// ---------------------------------------------------------------------------
// Session limits
// ---------------------------------------------------------------------------

/**
 * Maximum session duration in milliseconds (5 minutes).
 * Corresponds to 30,000 frames at 100Hz.
 */
export const MAX_SESSION_DURATION_MS = 5 * 60 * 1000;

/**
 * Maximum number of frames per session.
 * 5 minutes at 100Hz = 30,000 frames.
 */
export const MAX_FRAMES_PER_SESSION = 30_000;

/**
 * Sensor sampling rate in Hertz.
 */
export const SENSOR_SAMPLE_RATE_HZ = 100;

// ---------------------------------------------------------------------------
// Ingestion limits (POST /sessions/{id}/frames)
// ---------------------------------------------------------------------------

/**
 * Minimum number of frames per ingestion request.
 * Matches backend: `len(frames) < 1000` is rejected.
 */
export const MIN_FRAMES_PER_REQUEST = 1000;

/**
 * Maximum number of frames per ingestion request.
 * Matches backend: `len(frames) > 5000` is rejected.
 */
export const MAX_FRAMES_PER_REQUEST = 5000;

// ---------------------------------------------------------------------------
// Pagination limits (GET /sessions/{id})
// ---------------------------------------------------------------------------

/**
 * Default page size for frame pagination.
 * Matches backend default: `limit: int = Query(1000, ...)`.
 */
export const DEFAULT_PAGE_SIZE = 1000;

/**
 * Maximum page size for frame pagination.
 * Matches backend: `le=10000`.
 */
export const MAX_PAGE_SIZE = 10_000;

// ---------------------------------------------------------------------------
// Sensor continuity thresholds
// ---------------------------------------------------------------------------

/**
 * Maximum allowed amps jump between consecutive frames (as a ratio).
 * Backend rejects frames where `|curr - prev| / |prev| > 0.20`.
 * 0.20 = 20%.
 */
export const MAX_AMPS_JUMP_RATIO = 0.20;

/**
 * Maximum allowed volts jump between consecutive frames (as a ratio).
 * Backend rejects frames where `|curr - prev| / |prev| > 0.10`.
 * 0.10 = 10%.
 */
export const MAX_VOLTS_JUMP_RATIO = 0.10;

// ---------------------------------------------------------------------------
// Thermal validation
// ---------------------------------------------------------------------------

/**
 * Exact number of readings required per thermal snapshot.
 * Matches backend: `min_length=5, max_length=5`.
 */
export const READINGS_PER_THERMAL_SNAPSHOT = 5;

/**
 * Tolerance for thermal distance interval matching in millimeters.
 * Backend allows ±0.1mm for distance consistency checks.
 */
export const THERMAL_DISTANCE_TOLERANCE_MM = 0.1;

// ---------------------------------------------------------------------------
// Error messages
// ---------------------------------------------------------------------------

/**
 * User-friendly error messages for common validation failures.
 * Use these in UI toasts, form errors, and alert dialogs.
 */
export const ERROR_MESSAGES = {
  SESSION_NOT_FOUND: "Session not found. It may have been deleted.",
  SESSION_LOCKED:
    "Session is currently being uploaded to. Please wait and try again.",
  SESSION_COMPLETE:
    "This session is complete and cannot accept new frames.",
  FRAMES_OUT_OF_ORDER:
    "Frames must be in chronological order with 10ms intervals.",
  DUPLICATE_TIMESTAMPS: "Duplicate frame timestamps detected.",
  FRAME_GAP_DETECTED:
    "Gap detected in frame sequence. Expected continuous 10ms intervals.",
  THERMAL_DISTANCE_MISMATCH:
    "Thermal snapshot distances are inconsistent with session configuration.",
  AMPS_JUMP_TOO_LARGE:
    "Amps reading jumped more than 20% between consecutive frames.",
  VOLTS_JUMP_TOO_LARGE:
    "Volts reading jumped more than 10% between consecutive frames.",
  PAYLOAD_TOO_LARGE:
    "Session has too many frames. Use pagination or streaming to fetch data.",
  NETWORK_ERROR:
    "Network error. Please check your connection and try again.",
  UNKNOWN_ERROR:
    "An unexpected error occurred. Please try again or contact support.",
} as const;

// ---------------------------------------------------------------------------
// Validation rules summary
// ---------------------------------------------------------------------------

/**
 * Frontend validation rules — a quick-reference object.
 *
 * These mirror backend constraints and can be used to build
 * form validators, display warnings, or pre-validate before API calls.
 */
export const VALIDATION_RULES = {
  frame_interval_ms: FRAME_INTERVAL_MS,
  frame_interval_tolerance_ms: FRAME_INTERVAL_TOLERANCE_MS,
  thermal_sample_interval_ms: THERMAL_SAMPLE_INTERVAL_MS,
  max_session_duration_ms: MAX_SESSION_DURATION_MS,
  max_frames_per_session: MAX_FRAMES_PER_SESSION,
  min_frames_per_request: MIN_FRAMES_PER_REQUEST,
  max_frames_per_request: MAX_FRAMES_PER_REQUEST,
  max_page_size: MAX_PAGE_SIZE,
  max_amps_jump_ratio: MAX_AMPS_JUMP_RATIO,
  max_volts_jump_ratio: MAX_VOLTS_JUMP_RATIO,
  readings_per_thermal_snapshot: READINGS_PER_THERMAL_SNAPSHOT,
  thermal_distance_tolerance_mm: THERMAL_DISTANCE_TOLERANCE_MM,
} as const;
