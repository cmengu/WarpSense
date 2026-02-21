// AGENT 2 ADDITIONS — append to my-app/src/lib/api.ts
// Add import: import type { WarpRiskResponse } from "@/types/prediction";
// Uses buildUrl and apiFetch (same pattern as fetchSession, fetchScore).

/**
 * Fetch warp risk for a session.
 * @throws Error if not found (404) or request fails.
 */
export async function fetchWarpRisk(
  sessionId: string
): Promise<WarpRiskResponse> {
  const url = buildUrl(
    `/api/sessions/${encodeURIComponent(sessionId)}/warp-risk`
  );
  return apiFetch<WarpRiskResponse>(url);
}
