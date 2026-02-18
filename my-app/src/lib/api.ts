/**
 * API client for the Shipyard Welding backend.
 *
 * All functions communicate with the FastAPI backend at `API_BASE_URL`.
 * Types match the backend Pydantic models exactly (snake_case).
 *
 * Error handling:
 *   - Network failures throw with a descriptive message.
 *   - Non-2xx responses throw with status + backend detail message.
 *   - Callers should catch and display errors to the operator.
 */

import type { ActiveThresholdSpec } from "@/types/thresholds";
import type { WeldTypeThresholds } from "@/types/thresholds";
import type { AggregateKPIResponse } from "@/types/aggregate";
import type { DashboardData } from "@/types/dashboard";
import type { Frame } from "@/types/frame";
import type { Session } from "@/types/session";

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/**
 * Backend API base URL.
 * Set via NEXT_PUBLIC_API_URL environment variable.
 * Falls back to localhost:8000 for local development.
 *
 * Environment switching:
 * - Local: Unset (default localhost:8000)
 * - Dev/staging: NEXT_PUBLIC_API_URL=http://dev-server:8000
 * - Production: NEXT_PUBLIC_API_URL=https://api.example.com
 * Rebuild required when backend URL changes (baked at build time).
 */
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Shared types
// ---------------------------------------------------------------------------

/**
 * Query parameters for fetching a session.
 * All fields are optional — the backend applies defaults.
 */
export interface FetchSessionParams {
  /** Include thermal snapshot data in frames. Default: true. */
  include_thermal?: boolean;
  /** Start of time range filter in milliseconds. */
  time_range_start?: number;
  /** End of time range filter in milliseconds. */
  time_range_end?: number;
  /** Maximum number of frames to return. Default: 1000. Range: 1–10000. */
  limit?: number;
  /** Pagination offset (0-based). Default: 0. */
  offset?: number;
  /** Enable streaming for large sessions. Default: false. */
  stream?: boolean;
}

/**
 * Error detail for a single failed frame during ingestion.
 */
export interface FrameError {
  /** Index of the failed frame in the request (null if global error). */
  index: number | null;
  /** Timestamp of the failed frame (null if global error). */
  timestamp_ms: number | null;
  /** Human-readable error message. */
  error: string;
}

/**
 * Response from the POST /sessions/{session_id}/frames endpoint.
 */
export interface AddFramesResponse {
  /** "success" or "failed". */
  status: "success" | "failed";
  /** Number of frames successfully ingested. */
  successful_count: number;
  /** Per-frame error details (empty on success). */
  failed_frames: FrameError[];
  /** Next expected timestamp_ms for continuity. Null on failure. */
  next_expected_timestamp: number | null;
  /** Whether the client can resume uploading from next_expected_timestamp. */
  can_resume: boolean;
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Build a URL with query parameters, omitting undefined values.
 *
 * @param path - API path (e.g. "/api/sessions/sess_001").
 * @param params - Key-value pairs to append as query string.
 * @returns Fully formed URL string.
 */
function buildUrl(
  path: string,
  params: Record<string, string | number | boolean | undefined> = {}
): string {
  const url = new URL(path, API_BASE_URL);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) {
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

/**
 * Perform a fetch and handle common error patterns.
 *
 * @param url - Fully formed URL.
 * @param init - Fetch options (method, headers, body, etc.).
 * @returns Parsed JSON response.
 * @throws Error with descriptive message on failure.
 */
async function apiFetch<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, init);
  } catch (networkError) {
    // Network-level failure (DNS, connection refused, etc.)
    throw new Error(
      `Network error fetching ${url}: ${
        networkError instanceof Error ? networkError.message : String(networkError)
      }`
    );
  }

  if (!response.ok) {
    // Try to extract backend error detail (FastAPI returns detail as string or array of { msg, type, ... })
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (body.detail !== undefined) {
        detail = Array.isArray(body.detail)
          ? body.detail
              .map((d: { msg?: string }) => d.msg ?? JSON.stringify(d))
              .join("; ")
          : String(body.detail);
      }
    } catch {
      // Response body wasn't JSON — use statusText
    }
    throw new Error(`API error ${response.status}: ${detail}`);
  }

  return response.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

/**
 * Fetch dashboard overview data.
 *
 * @returns Dashboard metrics and charts.
 * @throws Error if the request fails.
 */
export async function fetchDashboardData(): Promise<DashboardData> {
  const url = buildUrl("/api/dashboard");
  return apiFetch<DashboardData>(url);
}

// ---------------------------------------------------------------------------
// Sessions
// ---------------------------------------------------------------------------

/**
 * Request body for creating a new session.
 */
export interface CreateSessionRequest {
  /** Operator identifier for audit. */
  operator_id: string;
  /** Weld type identifier (e.g. "mild_steel"). */
  weld_type: string;
  /** Optional session ID. If omitted, backend generates one. */
  session_id?: string;
}

/**
 * Response from POST /api/sessions.
 */
export interface CreateSessionResponse {
  /** The created session ID. Use with addFrames() and fetchSession(). */
  session_id: string;
}

/**
 * Create a new welding session in RECORDING status.
 *
 * Use the returned session_id when calling addFrames() to ingest frame data.
 *
 * @param body - Operator ID, weld type, and optional session ID.
 * @returns Created session ID.
 * @throws Error if session_id already exists (409) or request fails.
 */
export async function createSession(
  body: CreateSessionRequest
): Promise<CreateSessionResponse> {
  const url = buildUrl("/api/sessions");
  return apiFetch<CreateSessionResponse>(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

/**
 * Fetch a single welding session with its frames.
 *
 * Supports pagination (limit/offset), time range filtering,
 * thermal data toggling, and streaming for large sessions.
 *
 * @param sessionId - Unique session identifier.
 * @param params - Optional query parameters for filtering/pagination.
 * @returns Session object with frames.
 * @throws Error if session not found (404) or request fails.
 *
 * @example
 * ```typescript
 * // Fetch first 1000 frames
 * const session = await fetchSession("sess_001");
 *
 * // Fetch frames 1000–2000, without thermal data
 * const page2 = await fetchSession("sess_001", {
 *   offset: 1000,
 *   limit: 1000,
 *   include_thermal: false,
 * });
 *
 * // Fetch specific time range
 * const slice = await fetchSession("sess_001", {
 *   time_range_start: 5000,
 *   time_range_end: 10000,
 * });
 * ```
 */
export async function fetchSession(
  sessionId: string,
  params: FetchSessionParams = {}
): Promise<Session> {
  const url = buildUrl(`/api/sessions/${encodeURIComponent(sessionId)}`, {
    include_thermal: params.include_thermal,
    time_range_start: params.time_range_start,
    time_range_end: params.time_range_end,
    limit: params.limit,
    offset: params.offset,
    stream: params.stream,
  });
  return apiFetch<Session>(url);
}

/**
 * Score for a single rule (actual vs threshold).
 */
export interface ScoreRule {
  /** Rule identifier (e.g. amps_stability). */
  rule_id: string;
  /** Threshold value; pass when actual_value <= threshold. */
  threshold: number;
  /** Whether the rule passed. */
  passed: boolean;
  /** Measured value for "actual vs threshold" display. */
  actual_value: number | null;
}

/**
 * Session score with total and per-rule breakdown.
 */
export interface SessionScore {
  /** Total score 0–100 (passed_rules * 20). */
  total: number;
  /** Per-rule results with actual_value. */
  rules: ScoreRule[];
  /** Active threshold spec used for scoring (for micro-feedback and callouts). */
  active_threshold_spec?: ActiveThresholdSpec;
}

/**
 * Fetch score for a welding session.
 *
 * Backend loads session, extracts features, runs 5 rules, returns total + rules.
 *
 * @param sessionId - Session to score.
 * @returns SessionScore with total (0–100) and rules (✓/✗, threshold, actual_value).
 * @throws Error if session not found (404) or request fails.
 */
export async function fetchScore(
  sessionId: string
): Promise<SessionScore> {
  const url = buildUrl(`/api/sessions/${encodeURIComponent(sessionId)}/score`);
  return apiFetch<SessionScore>(url);
}

/**
 * Fetch all weld quality thresholds. Admin uses this to populate forms.
 */
export async function fetchThresholds(): Promise<WeldTypeThresholds[]> {
  const url = buildUrl("/api/thresholds");
  return apiFetch<WeldTypeThresholds[]>(url);
}

/**
 * Update thresholds for one process type. Returns the single updated threshold.
 */
export async function updateThreshold(
  weldType: string,
  body: Partial<WeldTypeThresholds>
): Promise<WeldTypeThresholds> {
  const url = buildUrl(`/api/thresholds/${encodeURIComponent(weldType)}`);
  return apiFetch<WeldTypeThresholds>(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ---------------------------------------------------------------------------
// Aggregate (WWAD Supervisor)
// ---------------------------------------------------------------------------

export interface FetchAggregateParams {
  date_start?: string;
  date_end?: string;
  include_sessions?: boolean;
}

/**
 * Fetch aggregate KPIs for supervisor dashboard.
 *
 * @param params - Optional date range and include_sessions for export.
 * @param signal - AbortSignal for cancellation.
 */
export async function fetchAggregateKPIs(
  params: FetchAggregateParams = {},
  signal?: AbortSignal
): Promise<AggregateKPIResponse> {
  const url = buildUrl("/api/sessions/aggregate", {
    date_start: params.date_start,
    date_end: params.date_end,
    include_sessions: params.include_sessions,
  } as Record<string, string | boolean | undefined>);
  return apiFetch<AggregateKPIResponse>(url, { signal });
}

// ---------------------------------------------------------------------------
// Frames
// ---------------------------------------------------------------------------

/**
 * Add frames to an existing session (incremental ingestion).
 *
 * Sends 1,000–5,000 frames per request. The backend validates
 * timestamp continuity, calculates heat dissipation, and inserts
 * in a single transaction.
 *
 * @param sessionId - Session to add frames to.
 * @param frames - Array of frames to ingest (1000–5000).
 * @returns Ingestion result with success/failure details.
 * @throws Error if session not found (404), locked (409), or request fails.
 *
 * @example
 * ```typescript
 * const result = await addFrames("sess_001", framesBatch);
 * if (result.status === "success") {
 *   // Use centralized logger for production
 *   // logError("addFrames", null, { count: result.successful_count, next: result.next_expected_timestamp });
 * } else {
 *   // logError("addFrames", "Ingestion failed", { failed_frames: result.failed_frames });
 * }
 * ```
 */
export async function addFrames(
  sessionId: string,
  frames: Frame[]
): Promise<AddFramesResponse> {
  const url = buildUrl(
    `/api/sessions/${encodeURIComponent(sessionId)}/frames`
  );
  return apiFetch<AddFramesResponse>(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(frames),
  });
}

// ---------------------------------------------------------------------------
// Exported for testing
// ---------------------------------------------------------------------------

export { buildUrl, apiFetch, API_BASE_URL };
