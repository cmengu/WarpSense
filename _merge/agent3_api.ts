// AGENT 3 ADDITIONS — append to my-app/src/lib/api.ts
// Add import: import type { NarrativeResponse } from "@/types/narrative";
// Add import: import type { SessionID } from "@/types/shared"; (if not already present)

/**
 * Fetch cached narrative for a session.
 * Returns 404 if narrative not yet generated — use generateNarrative to create.
 */
export async function fetchNarrative(
  sessionId: SessionID
): Promise<NarrativeResponse> {
  const url = buildUrl(
    `/api/sessions/${encodeURIComponent(sessionId)}/narrative`
  );
  return apiFetch<NarrativeResponse>(url);
}

/**
 * Generate (or regenerate) AI narrative for a session.
 * Caches result; subsequent calls return cached unless forceRegenerate=true.
 */
export async function generateNarrative(
  sessionId: SessionID,
  forceRegenerate = false
): Promise<NarrativeResponse> {
  const url = buildUrl(
    `/api/sessions/${encodeURIComponent(sessionId)}/narrative`
  );
  return apiFetch<NarrativeResponse>(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ force_regenerate: forceRegenerate }),
  });
}
