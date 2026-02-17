/**
 * Tests for demo-tour-config.ts — tour step definitions.
 */

import { DEMO_TOUR_STEPS } from "@/lib/demo-tour-config";
import { NOVICE_SPIKE_MS } from "@/lib/demo-config";

describe("demo-tour-config", () => {
  it("DEMO_TOUR_STEPS has 4 steps", () => {
    expect(DEMO_TOUR_STEPS).toHaveLength(4);
  });

  it("step with id novice_spike has timestamp_ms === NOVICE_SPIKE_MS", () => {
    const step = DEMO_TOUR_STEPS.find((s) => s.id === "novice_spike");
    expect(step).toBeDefined();
    expect(step!.timestamp_ms).toBe(NOVICE_SPIKE_MS);
    expect(step!.timestamp_ms).toBe(2400);
  });

  it("last step has isLast true and nextLabel is See Team Management", () => {
    const last = DEMO_TOUR_STEPS[DEMO_TOUR_STEPS.length - 1];
    expect(last.isLast).toBe(true);
    expect(last.nextLabel).toBe("See Team Management");
  });
});
