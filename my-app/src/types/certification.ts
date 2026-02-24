/**
 * Types for certification standards and welder certification status.
 * Matches backend Pydantic models (snake_case).
 */
import type { CertificationStatus, WelderID } from "./shared";

export interface CertStandard {
  id: string;
  name: string;
  required_score: number;
  sessions_required: number;
  weld_type: string | null;
}

export interface CertificationStatusItem {
  cert_standard: CertStandard;
  status: CertificationStatus;
  evaluated_at: string;
  qualifying_sessions: number;
  sessions_needed: number;
  current_avg_score: number | null;
  sessions_to_target: number | null;
  qualifying_session_ids: string[] | null;
}

export interface WelderCertificationSummary {
  welder_id: WelderID;
  certifications: CertificationStatusItem[];
}
