/**
 * Defect Library — cross-session searchable defect database.
 * Route: /defects
 * Orthogonal to WWAD supervisor page — no imports from supervisor/.
 */

"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  type DefectLibraryItem,
  ANNOTATION_TYPE_LABELS,
  ANNOTATION_TYPE_COLORS,
} from "@/types/annotation";
import type { AnnotationType } from "@/types/shared";
import { fetchDefectLibrary } from "@/lib/api";
import { logError } from "@/lib/logger";

const ALL_TYPES: Array<{ value: AnnotationType | ""; label: string }> = [
  { value: "", label: "All Types" },
  { value: "defect_confirmed", label: "Confirmed Defects" },
  { value: "near_miss", label: "Near Misses" },
  { value: "technique_error", label: "Technique Errors" },
  { value: "equipment_issue", label: "Equipment Issues" },
];

export default function DefectLibraryPage() {
  const [items, setItems] = useState<DefectLibraryItem[]>([]);
  const [filterType, setFilterType] = useState<AnnotationType | "">("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setError(null);
    setLoading(true);
    fetchDefectLibrary({ annotation_type: filterType || undefined })
      .then((data) => {
        if (mounted) {
          setItems(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        logError("DefectLibraryPage", err);
        if (mounted) {
          setError("Failed to load defect library.");
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [filterType]);

  return (
    <div className="min-h-screen bg-neutral-950 text-white px-8 py-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-bold">Defect Pattern Library</h1>
          <div className="flex gap-2">
            {ALL_TYPES.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                onClick={() => setFilterType(value)}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  filterType === value
                    ? "bg-cyan-500 text-black"
                    : "bg-neutral-800 text-neutral-400 hover:text-white"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {loading && (
          <div className="space-y-2" aria-live="polite" aria-busy="true">
            {[1, 2, 3].map((i) => (
              <div
                key={`skeleton-${i}`}
                className="h-16 bg-neutral-900 rounded animate-pulse"
              />
            ))}
          </div>
        )}

        {error && (
          <p className="text-red-400 text-sm" aria-live="polite">
            {error}
          </p>
        )}

        {!loading && !error && items.length === 0 && (
          <p className="text-neutral-500 text-sm text-center mt-12">
            No annotations yet. Add annotations in the Replay view.
          </p>
        )}

        {!loading && !error && items.length > 0 && (
          <div className="space-y-2">
            {items.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between rounded-lg border border-neutral-800 bg-neutral-900 px-4 py-3"
              >
                <div className="flex items-center gap-4">
                  <span
                    className={`text-xs font-semibold border rounded px-2 py-0.5 ${
                      ANNOTATION_TYPE_COLORS[item.annotation_type] ??
                      "text-neutral-400 border-neutral-500"
                    }`}
                  >
                    {ANNOTATION_TYPE_LABELS[item.annotation_type] ??
                      item.annotation_type}
                  </span>
                  <div>
                    <p className="text-sm text-white">
                      {item.note || "No note"}
                    </p>
                    <p className="text-xs text-neutral-500 mt-0.5">
                      {item.weld_type?.toUpperCase() ?? "Unknown"} ·{" "}
                      {item.operator_id ?? "Unknown"} ·{" "}
                      {new Date(item.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <Link
                  href={`/replay/${item.session_id}?t=${item.timestamp_ms}`}
                  className="text-xs text-cyan-400 hover:text-cyan-300 whitespace-nowrap ml-4"
                >
                  View in Replay →
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
