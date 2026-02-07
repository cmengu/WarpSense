/**
 * Hook for validating and formatting session metadata.
 *
 * Centralizes session metadata access so components don't need
 * to parse dates, look up labels, or validate IDs themselves.
 */

import { useMemo } from "react";

import type { Session, SessionStatus } from "@/types/session";
import { METAL_TYPE_LABELS } from "@/constants/metals";
import type { MetalType } from "@/constants/metals";

// ---------------------------------------------------------------------------
// Return type
// ---------------------------------------------------------------------------

export interface SessionMetadataResult {
  /** Session ID (pass-through). */
  session_id: string;
  /** Operator ID (pass-through). */
  operator_id: string;
  /** Parsed start time as a Date object. Null if unparseable. */
  start_date: Date | null;
  /** Formatted start time string for display (e.g. "Feb 7, 2026, 10:00 AM"). */
  start_time_display: string;
  /** Weld type identifier (pass-through). */
  weld_type: string;
  /** Human-readable weld type label (from METAL_TYPE_LABELS, or raw value). */
  weld_type_label: string;
  /** Current session status. */
  status: SessionStatus;
  /** Total frames ingested. */
  frame_count: number;
  /** Session duration in milliseconds (derived from frame data). */
  duration_ms: number;
  /** Formatted duration for display (e.g. "1m 30s"). */
  duration_display: string;
  /** Whether the session is still recording. */
  is_recording: boolean;
  /** Whether the session is complete. */
  is_complete: boolean;
  /** Validation errors (pass-through). */
  validation_errors: string[];
}

// ---------------------------------------------------------------------------
// Helpers (pure, deterministic)
// ---------------------------------------------------------------------------

/**
 * Format a duration in milliseconds to a human-readable string.
 *
 * @param ms - Duration in milliseconds.
 * @returns Formatted string (e.g. "2m 30s", "45s", "0s").
 */
export function formatDuration(ms: number): string {
  if (ms <= 0) return "0s";
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  if (minutes === 0) return `${seconds}s`;
  if (seconds === 0) return `${minutes}m`;
  return `${minutes}m ${seconds}s`;
}

/**
 * Format a Date for display. Returns a locale string or fallback.
 *
 * @param date - Date to format. Null if unparseable.
 * @returns Formatted date string, or "Invalid date".
 */
export function formatStartTime(date: Date | null): string {
  if (!date || isNaN(date.getTime())) return "Invalid date";
  return date.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/**
 * Look up a human-readable label for a weld type.
 * Falls back to the raw value if not found in METAL_TYPE_LABELS.
 *
 * @param weldType - Weld type identifier.
 * @returns Display label.
 */
export function getWeldTypeLabel(weldType: string): string {
  if (weldType in METAL_TYPE_LABELS) {
    return METAL_TYPE_LABELS[weldType as MetalType];
  }
  return weldType;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * React hook that derives formatted metadata from a Session.
 *
 * All computations are memoized on the session reference.
 *
 * @param session - The session to extract metadata from. Null if not loaded.
 * @returns Formatted metadata, or null if session is null.
 */
export function useSessionMetadata(
  session: Session | null
): SessionMetadataResult | null {
  return useMemo(() => {
    if (!session) return null;

    const startDate = new Date(session.start_time);
    const parsedDate = isNaN(startDate.getTime()) ? null : startDate;

    // Duration = last frame timestamp (or 0 if no frames)
    const lastTimestamp =
      session.frames.length > 0
        ? session.frames[session.frames.length - 1].timestamp_ms
        : 0;

    return {
      session_id: session.session_id,
      operator_id: session.operator_id,
      start_date: parsedDate,
      start_time_display: formatStartTime(parsedDate),
      weld_type: session.weld_type,
      weld_type_label: getWeldTypeLabel(session.weld_type),
      status: session.status,
      frame_count: session.frame_count,
      duration_ms: lastTimestamp,
      duration_display: formatDuration(lastTimestamp),
      is_recording: session.status === "recording",
      is_complete: session.status === "complete",
      validation_errors: session.validation_errors,
    };
  }, [session]);
}
