/**
 * WarpSense typed fetch helpers.
 *
 * All calls use same-origin Next `/api/warp/*` Route Handlers.
 *
 * streamAnalysis() uses the `/api/warp/sessions/[id]/analyse` proxy route which
 * pipes the FastAPI SSE body directly via `new Response(upstream.body)` with
 * `X-Accel-Buffering: no` — no buffering occurs. Keeping it same-origin avoids
 * CORS configuration requirements on the backend.
 * Backend route is POST-only; EventSource (GET) does not apply.
 *
 * fetchWarpHealth() never throws — returns both=false on network error.
 */
import type {
  MockSession,
  WarpReport,
  WarpHealthResponse,
  WelderTrendPoint,
  SimulatorInput,
  SimulatorResult,
} from "@/types/warp-analysis";

export async function fetchMockSessions(): Promise<MockSession[]> {
  const res = await fetch("/api/warp/mock-sessions");
  if (!res.ok) throw new Error(`fetchMockSessions: ${res.status}`);
  return res.json() as Promise<MockSession[]>;
}

/** Returns null on 404 (not yet analysed). Throws on other errors. */
export async function fetchWarpReport(sessionId: string): Promise<WarpReport | null> {
  const res = await fetch(`/api/warp/sessions/${sessionId}/reports`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`fetchWarpReport: ${res.status}`);
  return res.json() as Promise<WarpReport>;
}

/**
 * Returns raw ReadableStream for SSE consumption.
 * Caller decodes lines and parses "data: {...}\n\n" format.
 * Routes through the same-origin Next.js proxy which pipes the upstream body
 * directly with X-Accel-Buffering: no — no buffering occurs.
 */
export async function streamAnalysis(sessionId: string): Promise<ReadableStream<Uint8Array>> {
  const url = `/api/warp/sessions/${encodeURIComponent(sessionId)}/analyse`;
  const res = await fetch(url, {
    method: "POST",
    headers: { Accept: "text/event-stream" },
  });
  if (!res.ok || !res.body) throw new Error(`streamAnalysis: ${res.status}`);
  return res.body;
}

export async function fetchWarpHealth(): Promise<WarpHealthResponse> {
  try {
    const res = await fetch("/api/warp/health");
    if (!res.ok) return { graph_initialised: false, classifier_initialised: false };
    return res.json() as Promise<WarpHealthResponse>;
  } catch {
    return { graph_initialised: false, classifier_initialised: false };
  }
}

/**
 * Returns quality trend for the given welder (last 10 analysed sessions, oldest first).
 * Returns [] on 404 (no sessions analysed yet for this welder).
 * Throws on other errors.
 */
export async function fetchWelderTrend(welderId: string): Promise<WelderTrendPoint[]> {
  const res = await fetch(`/api/warp/welders/${encodeURIComponent(welderId)}/quality-trend`);
  if (res.status === 404) return [];
  if (!res.ok) throw new Error(`fetchWelderTrend: ${res.status}`);
  return res.json() as Promise<WelderTrendPoint[]>;
}

export async function simulateWeld(input: SimulatorInput): Promise<SimulatorResult> {
  const res = await fetch("/api/warp/simulator", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`simulateWeld HTTP ${res.status}`);
  return res.json() as Promise<SimulatorResult>;
}
