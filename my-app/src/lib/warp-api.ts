/**
 * WarpSense typed fetch helpers.
 *
 * Most calls use same-origin Next `/api/warp/*` Route Handlers (JSON proxies).
 *
 * streamAnalysis() is an exception: it POSTs directly to FastAPI
 * (`NEXT_PUBLIC_API_URL` + `/api/sessions/{id}/analyse`) so the SSE body is not
 * buffered by the Next.js proxy. Requires CORS (see backend CORS_ORIGINS).
 * Still uses fetch + ReadableStream — backend route is POST; EventSource is GET-only.
 *
 * fetchWarpHealth() never throws — returns both=false on network error.
 */
import type { MockSession, WarpReport, WarpHealthResponse, WelderTrendPoint } from "@/types/warp-analysis";
import { getBackendBaseUrl } from "@/lib/backend-base-url";

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
 * Direct to FastAPI — avoids Next route-handler buffering on SSE.
 */
export async function streamAnalysis(sessionId: string): Promise<ReadableStream<Uint8Array>> {
  const base = getBackendBaseUrl();
  const url = `${base}/api/sessions/${encodeURIComponent(sessionId)}/analyse`;
  const res = await fetch(url, {
    method: "POST",
    headers: { Accept: "text/event-stream" },
    mode: "cors",
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
