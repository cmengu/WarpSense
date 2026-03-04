/**
 * Panel readiness dashboard types.
 * PanelRiskLevel avoids collision with RiskLevel in @/types/shared ("ok" | "warning" | "critical").
 */

export type InspectionDecision =
  | "clear"
  | "needs-dpi"
  | "needs-xray"
  | "needs-surveyor";

export type ConstructionStage = "panel" | "block" | "ship";

export type PanelRiskLevel = "green" | "amber" | "red";

export interface Panel {
  id: string; // e.g. "PANEL-4C"
  label: string; // e.g. "Deck Plate — Port Side"
  blockId: string; // e.g. "B04"
  blockLabel: string; // e.g. "Block 04 · Midship"
  stage: ConstructionStage;
  jointsComplete: number;
  jointsTotal: number;
  inspectionDecision: InspectionDecision;
  trend: number | null; // % change, same shape as current welder trend
  sessionCount: number; // weld passes run on this panel
}

export interface PanelScoreResult {
  panel: Panel;
  score: number | null;
  riskLevel: PanelRiskLevel;
}
