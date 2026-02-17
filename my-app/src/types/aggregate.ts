/**
 * Types for WWAD aggregate API response.
 * Mirrors backend AggregateKPIResponse.
 */

export interface AggregateKPIs {
  avg_score: number | null;
  session_count: number;
  top_performer: string | null;
  rework_count: number;
}

export interface TrendPoint {
  date: string;
  value: number;
}

export interface CalendarDay {
  date: string;
  value: number;
}

export interface SessionSummary {
  session_id: string;
  operator_id: string;
  weld_type: string;
  start_time: string;
  score_total: number | null;
  frame_count: number;
}

export interface AggregateKPIResponse {
  kpis: AggregateKPIs;
  trend: TrendPoint[];
  calendar: CalendarDay[];
  sessions?: SessionSummary[];
  sessions_truncated?: boolean;
}
