/**
 * Tests for frontend Comparison types (Step 12).
 *
 * Validates:
 *   - TemperatureDelta, ThermalDelta, FrameDelta structures
 *   - snake_case naming matches backend
 *   - Generic comparison (no role assumption)
 *   - validateFrameDelta() runtime checks
 *   - Sign convention (session_a - session_b)
 *   - Null handling for optional delta fields
 */

import type {
  FrameDelta,
  TemperatureDelta,
  ThermalDelta,
} from "@/types/comparison";
import { validateFrameDelta } from "@/types/comparison";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a valid TemperatureDelta. */
function makeTempDelta(
  direction: string = "center",
  delta: number = 15.2
): TemperatureDelta {
  return { direction, delta_temp_celsius: delta };
}

/** Build a valid ThermalDelta with all 5 directions. */
function makeThermalDelta(distance_mm: number = 10.0): ThermalDelta {
  return {
    distance_mm,
    readings: [
      makeTempDelta("center", 15.2),
      makeTempDelta("north", 8.7),
      makeTempDelta("south", 12.1),
      makeTempDelta("east", -3.4),
      makeTempDelta("west", 5.6),
    ],
  };
}

/** Build a valid FrameDelta with all fields populated. */
function makeFrameDelta(overrides: Partial<FrameDelta> = {}): FrameDelta {
  return {
    timestamp_ms: 100,
    amps_delta: 5.0,
    volts_delta: -1.2,
    angle_degrees_delta: 3.5,
    heat_dissipation_rate_celsius_per_sec_delta: -0.8,
    thermal_deltas: [makeThermalDelta(10.0)],
    ...overrides,
  };
}

/** Build a FrameDelta with all optional fields null. */
function makeNullFrameDelta(overrides: Partial<FrameDelta> = {}): FrameDelta {
  return {
    timestamp_ms: 100,
    amps_delta: null,
    volts_delta: null,
    angle_degrees_delta: null,
    heat_dissipation_rate_celsius_per_sec_delta: null,
    thermal_deltas: [],
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// TemperatureDelta structure
// ---------------------------------------------------------------------------

describe("TemperatureDelta structure", () => {
  it("has direction and delta_temp_celsius fields (snake_case)", () => {
    const delta = makeTempDelta();
    expect("direction" in delta).toBe(true);
    expect("delta_temp_celsius" in delta).toBe(true);
  });

  it("positive delta means session_a is hotter", () => {
    const delta = makeTempDelta("center", 15.2);
    expect(delta.delta_temp_celsius).toBeGreaterThan(0);
  });

  it("negative delta means session_a is cooler", () => {
    const delta = makeTempDelta("east", -3.4);
    expect(delta.delta_temp_celsius).toBeLessThan(0);
  });

  it("zero delta means sessions match", () => {
    const delta = makeTempDelta("center", 0);
    expect(delta.delta_temp_celsius).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// ThermalDelta structure
// ---------------------------------------------------------------------------

describe("ThermalDelta structure", () => {
  it("has distance_mm and readings fields (snake_case)", () => {
    const td = makeThermalDelta();
    expect("distance_mm" in td).toBe(true);
    expect("readings" in td).toBe(true);
  });

  it("readings contain per-direction deltas", () => {
    const td = makeThermalDelta();
    expect(td.readings).toHaveLength(5);
    const dirs = td.readings.map((r) => r.direction);
    expect(dirs).toContain("center");
    expect(dirs).toContain("north");
    expect(dirs).toContain("south");
    expect(dirs).toContain("east");
    expect(dirs).toContain("west");
  });

  it("accepts empty readings array", () => {
    const td: ThermalDelta = { distance_mm: 10.0, readings: [] };
    expect(td.readings).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// FrameDelta structure — snake_case naming
// ---------------------------------------------------------------------------

describe("FrameDelta structure — snake_case field names", () => {
  it("has all expected keys", () => {
    const delta = makeFrameDelta();
    const keys = Object.keys(delta);
    expect(keys).toContain("timestamp_ms");
    expect(keys).toContain("amps_delta");
    expect(keys).toContain("volts_delta");
    expect(keys).toContain("angle_degrees_delta");
    expect(keys).toContain("heat_dissipation_rate_celsius_per_sec_delta");
    expect(keys).toContain("thermal_deltas");
  });

  it("no camelCase keys exist", () => {
    const delta = makeFrameDelta();
    const keys = Object.keys(delta);
    expect(keys).not.toContain("timestampMs");
    expect(keys).not.toContain("ampsDelta");
    expect(keys).not.toContain("voltsDelta");
    expect(keys).not.toContain("angleDegreeDelta");
    expect(keys).not.toContain("thermalDeltas");
  });
});

// ---------------------------------------------------------------------------
// Generic comparison — no role assumption
// ---------------------------------------------------------------------------

describe("Generic comparison — no role assumption", () => {
  it("works for expert vs expert (deltas can be small)", () => {
    const delta = makeFrameDelta({
      amps_delta: 0.5,
      volts_delta: 0.1,
      angle_degrees_delta: 0.3,
    });
    const errors = validateFrameDelta(delta);
    expect(errors).toEqual([]);
  });

  it("works for novice vs novice (deltas can be large)", () => {
    const delta = makeFrameDelta({
      amps_delta: 50.0,
      volts_delta: -10.0,
      angle_degrees_delta: 25.0,
    });
    const errors = validateFrameDelta(delta);
    expect(errors).toEqual([]);
  });

  it("works for expert vs novice (mixed signs)", () => {
    const delta = makeFrameDelta({
      amps_delta: -20.0,
      volts_delta: 5.0,
      angle_degrees_delta: -15.0,
    });
    const errors = validateFrameDelta(delta);
    expect(errors).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Null handling
// ---------------------------------------------------------------------------

describe("FrameDelta — null handling", () => {
  it("accepts all-null optional delta fields", () => {
    const delta = makeNullFrameDelta();
    const errors = validateFrameDelta(delta);
    expect(errors).toEqual([]);
  });

  it("accepts mixed null and present fields", () => {
    const delta = makeFrameDelta({
      amps_delta: 5.0,
      volts_delta: null,
      angle_degrees_delta: null,
      heat_dissipation_rate_celsius_per_sec_delta: -0.8,
    });
    const errors = validateFrameDelta(delta);
    expect(errors).toEqual([]);
  });

  it("accepts empty thermal_deltas array", () => {
    const delta = makeFrameDelta({ thermal_deltas: [] });
    const errors = validateFrameDelta(delta);
    expect(errors).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// validateFrameDelta — valid cases
// ---------------------------------------------------------------------------

describe("validateFrameDelta — valid cases", () => {
  it("returns no errors for a fully populated delta", () => {
    const errors = validateFrameDelta(makeFrameDelta());
    expect(errors).toEqual([]);
  });

  it("returns no errors for a minimal delta (all nulls, no thermal)", () => {
    const errors = validateFrameDelta(makeNullFrameDelta());
    expect(errors).toEqual([]);
  });

  it("accepts timestamp_ms = 0", () => {
    const errors = validateFrameDelta(makeFrameDelta({ timestamp_ms: 0 }));
    expect(errors).toEqual([]);
  });

  it("accepts multiple thermal deltas at different distances", () => {
    const delta = makeFrameDelta({
      thermal_deltas: [
        makeThermalDelta(10.0),
        makeThermalDelta(20.0),
        makeThermalDelta(30.0),
      ],
    });
    const errors = validateFrameDelta(delta);
    expect(errors).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// validateFrameDelta — invalid cases
// ---------------------------------------------------------------------------

describe("validateFrameDelta — invalid timestamp", () => {
  it("rejects negative timestamp_ms", () => {
    const errors = validateFrameDelta(makeFrameDelta({ timestamp_ms: -1 }));
    expect(errors.some((e) => e.includes("non-negative integer"))).toBe(true);
  });

  it("rejects non-integer timestamp_ms", () => {
    const errors = validateFrameDelta(makeFrameDelta({ timestamp_ms: 10.5 }));
    expect(errors.some((e) => e.includes("non-negative integer"))).toBe(true);
  });
});

describe("validateFrameDelta — invalid numeric deltas", () => {
  it("rejects NaN in amps_delta", () => {
    const errors = validateFrameDelta(makeFrameDelta({ amps_delta: NaN }));
    expect(errors.some((e) => e.includes("amps_delta"))).toBe(true);
  });

  it("rejects Infinity in volts_delta", () => {
    const errors = validateFrameDelta(
      makeFrameDelta({ volts_delta: Infinity })
    );
    expect(errors.some((e) => e.includes("volts_delta"))).toBe(true);
  });

  it("rejects -Infinity in angle_degrees_delta", () => {
    const errors = validateFrameDelta(
      makeFrameDelta({ angle_degrees_delta: -Infinity })
    );
    expect(errors.some((e) => e.includes("angle_degrees_delta"))).toBe(true);
  });

  it("rejects NaN in heat_dissipation_rate_celsius_per_sec_delta", () => {
    const errors = validateFrameDelta(
      makeFrameDelta({
        heat_dissipation_rate_celsius_per_sec_delta: NaN,
      })
    );
    expect(
      errors.some((e) =>
        e.includes("heat_dissipation_rate_celsius_per_sec_delta")
      )
    ).toBe(true);
  });
});

describe("validateFrameDelta — invalid thermal delta distances", () => {
  it("rejects zero distance_mm in thermal delta", () => {
    const delta = makeFrameDelta({
      thermal_deltas: [makeThermalDelta(0)],
    });
    const errors = validateFrameDelta(delta);
    expect(
      errors.some((e) => e.includes("thermal_deltas[0].distance_mm"))
    ).toBe(true);
  });

  it("rejects negative distance_mm in thermal delta", () => {
    const delta = makeFrameDelta({
      thermal_deltas: [makeThermalDelta(-5.0)],
    });
    const errors = validateFrameDelta(delta);
    expect(
      errors.some((e) => e.includes("thermal_deltas[0].distance_mm"))
    ).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Type-level compile-time checks
// ---------------------------------------------------------------------------

describe("Type-level compile-time safety", () => {
  it("FrameDelta requires all fields", () => {
    const delta: FrameDelta = makeFrameDelta();
    expect(Object.keys(delta)).toHaveLength(6);
  });

  it("ThermalDelta requires distance_mm and readings", () => {
    const td: ThermalDelta = { distance_mm: 10.0, readings: [] };
    expect(Object.keys(td)).toEqual(
      expect.arrayContaining(["distance_mm", "readings"])
    );
  });

  it("TemperatureDelta requires direction and delta_temp_celsius", () => {
    const d: TemperatureDelta = { direction: "center", delta_temp_celsius: 0 };
    expect(Object.keys(d)).toEqual(
      expect.arrayContaining(["direction", "delta_temp_celsius"])
    );
  });
});
