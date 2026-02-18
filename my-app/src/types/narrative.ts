import type { SessionID } from "./shared";

export interface NarrativeResponse {
  session_id: SessionID;
  narrative_text: string;
  model_version: string;
  generated_at: string; // ISO 8601
  cached: boolean;
}
