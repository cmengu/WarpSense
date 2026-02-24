/**
 * Coaching plan types — drills and assignments.
 * Matches backend schemas/coaching.py responses.
 */
import type { WelderID, WeldMetric, CoachingStatus } from "./shared";

export interface Drill {
  id: number;
  target_metric: WeldMetric;
  title: string;
  description: string;
  sessions_required: number;
  success_threshold: number;
}

export interface CoachingAssignment {
  id: number;
  welder_id: WelderID;
  drill: Drill;
  assigned_at: string;
  status: CoachingStatus;
  sessions_completed: number;
  completed_at: string | null;
  current_metric_value: number | null;
}

export interface CoachingPlan {
  welder_id: WelderID;
  active_assignments: CoachingAssignment[];
  completed_assignments: CoachingAssignment[];
  auto_assigned: boolean;
}
