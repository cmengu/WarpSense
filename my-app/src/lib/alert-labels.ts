/**
 * Maps backend rule_triggered (snake_case) to investor-facing human-readable labels.
 * Used by compare page and realtime page to display professional alert text
 * instead of internal backend identifiers.
 * Backend rule names from alert_engine.py; fallback to raw value if unknown.
 */
export const RULE_LABELS: Record<string, string> = {
  rule1: 'Thermal asymmetry',
  rule2: 'Torch angle',
  rule3: 'Travel speed',
  porosity: 'Porosity',
  oxide_inclusion: 'Oxide Inclusion',
  undercut: 'Undercut',
  lack_of_fusion_amps: 'Lack of Fusion — Low Current',
  lack_of_fusion_speed: 'Lack of Fusion — High Speed',
  burn_through: 'Burn Through',
  crater_crack: 'Crater Crack Risk',
  arc_instability: 'Arc Instability',
};

/**
 * Returns human-readable label for rule_triggered; fallback to raw value if unknown.
 * Use this when rendering alerts to avoid leaking backend snake_case into the UI.
 * Defensive: returns '' if ruleTriggered is undefined/null/empty (API edge case).
 */
export function getRuleLabel(ruleTriggered: string | undefined | null): string {
  if (ruleTriggered == null || ruleTriggered === '') return '';
  return RULE_LABELS[ruleTriggered] ?? ruleTriggered;
}
