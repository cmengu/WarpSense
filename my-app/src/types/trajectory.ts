import type { WelderID, SessionID, MetricScore } from "./shared";

export interface TrajectoryPoint {
  session_id: SessionID;
  session_date: string; // ISO 8601
  score_total: number; // 0–100
  metrics: MetricScore[];
  session_index: number; // 1-based (contiguous when no skips)
}

export interface WelderTrajectory {
  welder_id: WelderID;
  points: TrajectoryPoint[];
  trend_slope: number | null; // positive = improving
  projected_next_score: number | null;
  skipped_sessions_count?: number | null;
}
