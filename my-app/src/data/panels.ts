/**
 * Shared panel data and session ID helpers.
 *
 * Used by dashboard (panel cards, "View weld passes" links) and panel passes page
 * (load all weld-pass sessions for a panel).
 */

import type { Panel } from "@/types/panel";

// ---------------------------------------------------------------------------
// PANELS
// ---------------------------------------------------------------------------

/** Panel readiness data — 6 panels with metadata. Shared by dashboard and panel passes page. */
export const PANELS: Panel[] = [
  {
    id: "PANEL-4C",
    label: "Deck Plate — Port Side",
    blockId: "B04",
    blockLabel: "Block 04 · Midship",
    stage: "panel",
    jointsComplete: 5,
    jointsTotal: 18,
    inspectionDecision: "needs-xray",
    sessionCount: 5,
  },
  {
    id: "PANEL-7A",
    label: "Bulkhead — Starboard",
    blockId: "B07",
    blockLabel: "Block 07 · Aft",
    stage: "panel",
    jointsComplete: 14,
    jointsTotal: 18,
    inspectionDecision: "needs-dpi",
    sessionCount: 5,
  },
  {
    id: "PANEL-2B",
    label: "Tank Top — Centre",
    blockId: "B02",
    blockLabel: "Block 02 · Forward",
    stage: "panel",
    jointsComplete: 10,
    jointsTotal: 18,
    inspectionDecision: "needs-dpi",
    sessionCount: 5,
  },
  {
    id: "PANEL-1A",
    label: "Keel Plate — Centre",
    blockId: "B01",
    blockLabel: "Block 01 · Forward",
    stage: "panel",
    jointsComplete: 18,
    jointsTotal: 18,
    inspectionDecision: "clear",
    sessionCount: 5,
  },
  {
    id: "PANEL-9D",
    label: "Side Shell — Port",
    blockId: "B09",
    blockLabel: "Block 09 · Midship",
    stage: "block",
    jointsComplete: 18,
    jointsTotal: 18,
    inspectionDecision: "clear",
    sessionCount: 5,
  },
  {
    id: "PANEL-3F",
    label: "Inner Bottom — Stbd",
    blockId: "B03",
    blockLabel: "Block 03 · Forward",
    stage: "block",
    jointsComplete: 18,
    jointsTotal: 18,
    inspectionDecision: "clear",
    sessionCount: 5,
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Latest pass only — used by dashboard "View weld passes" link.
 * Returns session ID for the most recent weld pass (e.g. sess_PANEL-2B_005).
 */
export function getSessionIdForPanel(panel: Panel): string {
  return `sess_${panel.id}_${String(panel.sessionCount).padStart(3, "0")}`;
}

/**
 * All pass session IDs _001 through _00N.
 * Assumption: sessions are numbered sequentially with no gaps (no deleted/skipped passes).
 * 404s on individual IDs are handled gracefully by the caller.
 */
export function getSessionIdsForPanel(panel: Panel): string[] {
  return Array.from({ length: panel.sessionCount }, (_, i) =>
    `sess_${panel.id}_${String(i + 1).padStart(3, "0")}`
  );
}
