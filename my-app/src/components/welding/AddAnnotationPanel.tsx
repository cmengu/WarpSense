/**
 * AddAnnotationPanel — click-to-annotate modal for replay page.
 * Shown when user enables "Annotate Mode" toggle.
 */

"use client";

import React, { useState } from "react";
import {
  type AnnotationCreate,
  ANNOTATION_TYPE_LABELS,
} from "@/types/annotation";
import type { AnnotationType, SessionID } from "@/types/shared";
import { createAnnotation } from "@/lib/api";
import { logError } from "@/lib/logger";

const ANNOTATION_TYPES: AnnotationType[] = [
  "defect_confirmed",
  "near_miss",
  "technique_error",
  "equipment_issue",
];

interface AddAnnotationPanelProps {
  sessionId: SessionID;
  selectedTimestampMs: number | null;
  onAnnotationSaved: () => void;
  onClose: () => void;
}

export function AddAnnotationPanel({
  sessionId,
  selectedTimestampMs,
  onAnnotationSaved,
  onClose,
}: AddAnnotationPanelProps) {
  const [type, setType] = useState<AnnotationType>("defect_confirmed");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    if (selectedTimestampMs === null) return;
    setSaving(true);
    setError(null);
    try {
      const body: AnnotationCreate = {
        timestamp_ms: selectedTimestampMs,
        annotation_type: type,
        note: note.trim() || undefined,
      };
      const created = await createAnnotation(sessionId, body);
      if (created?.id != null) {
        onAnnotationSaved();
        onClose();
      } else {
        setError("Unexpected response from server. Please try again.");
      }
    } catch (err) {
      logError("AddAnnotationPanel", err);
      setError("Failed to save annotation. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-lg border border-neutral-700 bg-neutral-900 p-4 w-72">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">Add Annotation</h3>
        <button
          type="button"
          onClick={onClose}
          className="text-neutral-500 hover:text-white text-lg leading-none"
          aria-label="Close"
        >
          ×
        </button>
      </div>

      {selectedTimestampMs !== null && (
        <p className="text-xs text-neutral-500 mb-3">
          At{" "}
          <span className="text-neutral-300">
            {(selectedTimestampMs / 1000).toFixed(2)}s
          </span>
        </p>
      )}

      <label className="block text-xs text-neutral-400 mb-1">Type</label>
      <select
        value={type}
        onChange={(e) => setType(e.target.value as AnnotationType)}
        className="w-full bg-neutral-800 border border-neutral-700 rounded px-2 py-1.5 text-sm text-white mb-3"
      >
        {ANNOTATION_TYPES.map((t) => (
          <option key={t} value={t}>
            {ANNOTATION_TYPE_LABELS[t]}
          </option>
        ))}
      </select>

      <label className="block text-xs text-neutral-400 mb-1">
        Note (optional)
      </label>
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        rows={2}
        maxLength={2000}
        placeholder="What did you observe?"
        className="w-full bg-neutral-800 border border-neutral-700 rounded px-2 py-1.5 text-sm text-white resize-none mb-3"
      />

      {error && <p className="text-xs text-red-400 mb-2">{error}</p>}

      <button
        type="button"
        onClick={handleSave}
        disabled={saving || selectedTimestampMs === null}
        className="w-full bg-cyan-500 hover:bg-cyan-400 disabled:bg-neutral-700 disabled:text-neutral-500 text-black font-semibold py-1.5 rounded text-sm"
      >
        {saving ? "Saving…" : "Save Annotation"}
      </button>
    </div>
  );
}

export default AddAnnotationPanel;
