/**
 * Type definitions for welding session data structures
 * Ensures type safety across all welding components
 * Matches Python Pydantic models for type alignment
 */

export interface SessionMeta {
  sessionId: string;
  startTimestampMs: number;
  firmwareVersion: string;
}

export interface HeatMapPoint {
  x_mm: number;
  y_mm: number;
  intensity_norm: number;
}

export interface ScoreRule {
  ruleId: string;
  threshold: number;
  passed: boolean;
}

export interface SessionScore {
  total: number;
  rules: ScoreRule[];
}

export interface WeldingSession {
  meta: SessionMeta;
  heatMap?: HeatMapPoint[];
  torchAngleDeg?: number[];
  score?: SessionScore;
}
