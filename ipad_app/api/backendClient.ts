/**
 * Backend API Client
 * REST calls to FastAPI backend
 *
 * PLACEHOLDER MODE: These functions return safe empty/placeholder values
 * until the backend integration is implemented. No errors are thrown.
 *
 * Set IMPLEMENT_BACKEND_CLIENT=1 when ready to wire real API calls.
 */

const API_URL = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000";

/** Minimal session shape for placeholder responses. */
interface PlaceholderSession {
  session_id: string;
  operator_id: string;
  start_time: string;
  weld_type: string;
  thermal_sample_interval_ms: number;
  thermal_directions: string[];
  thermal_distance_interval_mm: number;
  sensor_sample_rate_hz: number;
  frames: unknown[];
  status: string;
  frame_count: number;
  expected_frame_count: null;
  last_successful_frame_index: null;
  validation_errors: string[];
  completed_at: null;
}

function createEmptySession(sessionId: string): PlaceholderSession {
  return {
    session_id: sessionId,
    operator_id: "placeholder",
    start_time: new Date().toISOString(),
    weld_type: "placeholder",
    thermal_sample_interval_ms: 100,
    thermal_directions: ["center", "north", "south", "east", "west"],
    thermal_distance_interval_mm: 10,
    sensor_sample_rate_hz: 100,
    frames: [],
    status: "recording",
    frame_count: 0,
    expected_frame_count: null,
    last_successful_frame_index: null,
    validation_errors: [],
    completed_at: null,
  };
}

/**
 * Send session data to backend.
 * PLACEHOLDER: No-op, resolves successfully. Replace with real fetch when ready.
 */
export async function sendSession(sessionData: unknown): Promise<void> {
  // Placeholder — no-op until backend integration
  await Promise.resolve();
  if (process.env.NODE_ENV === "development") {
    // eslint-disable-next-line no-console
    console.debug("[backendClient] sendSession placeholder (not sent)", {
      frameCount: Array.isArray((sessionData as { frames?: unknown[] })?.frames)
        ? (sessionData as { frames: unknown[] }).frames.length
        : "?",
    });
  }
}

/**
 * Fetch session data from backend.
 * PLACEHOLDER: Returns empty session. Replace with real fetch when ready.
 */
export async function fetchSession(sessionId: string): Promise<PlaceholderSession | null> {
  // Placeholder — return empty session so callers don't crash
  return createEmptySession(sessionId);
}

/**
 * List all sessions.
 * PLACEHOLDER: Returns empty array. Replace with real fetch when ready.
 */
export async function listSessions(): Promise<PlaceholderSession[]> {
  // Placeholder — return empty list
  return [];
}
