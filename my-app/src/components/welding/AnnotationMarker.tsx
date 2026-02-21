/**
 * AnnotationMarker — renders annotation pins on replay timeline.
 * Follows same pattern as TimelineMarkers.tsx (read that file first).
 * Does NOT modify TimelineMarkers.tsx.
 */

"use client";

import React from "react";
import {
  type Annotation,
  ANNOTATION_TYPE_COLORS,
  ANNOTATION_TYPE_LABELS,
} from "@/types/annotation";

interface AnnotationMarkerProps {
  annotations: Annotation[];
  firstTimestamp: number;
  lastTimestamp: number;
  onAnnotationClick: (timestamp_ms: number) => void;
}

export function AnnotationMarker({
  annotations,
  firstTimestamp,
  lastTimestamp,
  onAnnotationClick,
}: AnnotationMarkerProps) {
  const range = lastTimestamp - firstTimestamp;
  if (range <= 0 || annotations.length === 0) return null;

  return (
    <div
      className="relative h-4 w-full"
      role="list"
      aria-label="Annotation markers"
    >
      {annotations.map((ann) => {
        const pct = ((ann.timestamp_ms - firstTimestamp) / range) * 100;
        const colorClass =
          ANNOTATION_TYPE_COLORS[ann.annotation_type] ?? "text-neutral-400 border-neutral-500";
        const label =
          ANNOTATION_TYPE_LABELS[ann.annotation_type] ?? ann.annotation_type;
        return (
          <button
            key={ann.id}
            type="button"
            role="listitem"
            title={`${label}${ann.note ? `: ${ann.note}` : ""}`}
            onClick={() => onAnnotationClick(ann.timestamp_ms)}
            style={{ left: `${pct}%` }}
            className={`absolute -translate-x-1/2 w-2 h-4 border-l-2 cursor-pointer opacity-80 hover:opacity-100 ${colorClass}`}
            aria-label={label}
          />
        );
      })}
    </div>
  );
}

export default AnnotationMarker;
