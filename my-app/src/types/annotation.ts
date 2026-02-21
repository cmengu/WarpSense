/**
 * Annotation types for session defect/near-miss/technique annotations.
 * Matches backend schemas.annotation and models.shared_enums.AnnotationType.
 */

import type { SessionID, AnnotationType } from "./shared";

export interface Annotation {
  id: number;
  session_id: SessionID;
  timestamp_ms: number;
  annotation_type: AnnotationType;
  note: string | null;
  created_by: string | null;
  created_at: string; // ISO 8601
}

export interface AnnotationCreate {
  timestamp_ms: number;
  annotation_type: AnnotationType;
  note?: string;
  created_by?: string;
}

export interface DefectLibraryItem extends Annotation {
  weld_type: string | null;
  operator_id: string | null;
}

export const ANNOTATION_TYPE_LABELS: Record<AnnotationType, string> = {
  defect_confirmed: "Confirmed Defect",
  near_miss: "Near Miss",
  technique_error: "Technique Error",
  equipment_issue: "Equipment Issue",
};

export const ANNOTATION_TYPE_COLORS: Record<AnnotationType, string> = {
  defect_confirmed: "text-red-400 border-red-500",
  near_miss: "text-amber-400 border-amber-500",
  technique_error: "text-orange-400 border-orange-500",
  equipment_issue: "text-violet-400 border-violet-500",
};
