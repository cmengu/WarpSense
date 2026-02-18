import type { RiskLevel, SessionID } from "./shared";

export interface WarpRiskResponse {
  session_id: SessionID;
  probability: number;
  risk_level: RiskLevel;
  model_available: boolean;
  window_frames_used: number;
}
