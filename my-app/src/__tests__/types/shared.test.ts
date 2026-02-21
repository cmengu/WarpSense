/**
 * Shared types tests — METRIC_LABELS / WELD_METRICS / RULE_TEMPLATES alignment.
 */
import { METRIC_LABELS, WELD_METRICS } from "@/types/shared";
import { RULE_TEMPLATES } from "@/lib/ai-feedback";

describe("shared types", () => {
  it("METRIC_LABELS has exactly the keys in WELD_METRICS", () => {
    const labelKeys = Object.keys(METRIC_LABELS).sort();
    const metricKeys = [...WELD_METRICS].sort();
    expect(labelKeys).toEqual(metricKeys);
  });

  it("every WELD_METRIC has a METRIC_LABELS entry", () => {
    for (const m of WELD_METRICS) {
      expect(METRIC_LABELS).toHaveProperty(m);
      expect(typeof METRIC_LABELS[m]).toBe("string");
    }
  });

  it("RULE_TEMPLATES keys equal WELD_METRICS (no drift)", () => {
    const templateKeys = Object.keys(RULE_TEMPLATES).sort();
    const metricKeys = [...WELD_METRICS].sort();
    expect(templateKeys).toEqual(metricKeys);
  });

  it("every RULE_TEMPLATES value is a callable function", () => {
    for (const m of WELD_METRICS) {
      expect(RULE_TEMPLATES).toHaveProperty(m);
      expect(typeof RULE_TEMPLATES[m]).toBe("function");
    }
  });
});
