/**
 * WarpSense post-weld analysis types.
 * Single source of truth — snake_case matches backend JSON exactly.
 */

export type WarpDisposition = "PASS" | "CONDITIONAL" | "REWORK_REQUIRED";

// GET /api/mock-sessions
export interface MockSession {
  session_id:   string;
  welder_id:    string;
  welder_name:  string;
  arc_type:     string;
  arc_on_ratio: number | null;
  disposition:  WarpDisposition | null;
  started_at:   string;
}

// SSE event (POST /api/sessions/{id}/analyse)
export type WarpSSEStage =
  | "start" | "thermal_agent" | "geometry_agent"
  | "process_agent" | "summary" | "complete" | "error";
export type WarpSSEStatus = "running" | "done" | "error";

export interface WarpSSEEvent {
  stage:        WarpSSEStage;
  status:       WarpSSEStatus;
  message?:     string;
  disposition?: WarpDisposition;
  report?:      WarpReport;
}

export interface ThresholdViolation {
  feature: string; value: number; threshold: number; severity: string;
}

// SSE `complete` payload minimum; GET `/reports` and future backend expansions
// may include the optional fields below.
export interface WarpReport {
  session_id:                string;
  quality_class:             string;
  confidence:                number;
  iso_5817_level:            string;
  disposition:               WarpDisposition;
  disposition_rationale:     string;
  root_cause:                string;
  corrective_actions:        string[];
  standards_references:      string[];
  primary_defect_categories: string[];
  threshold_violations:      ThresholdViolation[];
  self_check_passed:         boolean;
  self_check_notes:          string;
  report_timestamp:          string;
  report_id?:                number;
  retrieved_chunks_used?:    string[];
  agent_type?:               string;
  llm_raw_response?:         string | null;
}

// Specialist card state (AnalysisStream internal)
export type AgentStage = "thermal_agent" | "geometry_agent" | "process_agent";
export type AgentCardStatus = "queued" | "running" | "done";
export interface AgentCardState {
  status: AgentCardStatus;
  disposition: WarpDisposition | null;
}

// GET /api/health/warp
export interface WarpHealthResponse {
  graph_initialised:      boolean;
  classifier_initialised: boolean;
}

// GET /api/welders/{welder_id}/quality-trend — one item per analysed session
export interface WelderTrendPoint {
  session_id:        string;
  report_timestamp:  string;
  weld_type:         string | null;
  disposition:       WarpDisposition;
  quality_score:     number;
}
