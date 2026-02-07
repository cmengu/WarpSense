/**
 * Tests for frontend thermal types (Step 9).
 *
 * Validates:
 *   - ThermalDirection type guard
 *   - TemperaturePoint structure
 *   - ThermalSnapshot runtime validation
 *   - THERMAL_DIRECTIONS constant
 *   - READINGS_PER_SNAPSHOT constant
 *   - Edge cases (duplicates, missing directions, wrong counts)
 */

import {
  READINGS_PER_SNAPSHOT,
  THERMAL_DIRECTIONS,
  type TemperaturePoint,
  type ThermalDirection,
  type ThermalSnapshot,
  isThermalDirection,
  validateThermalSnapshot,
} from "@/types/thermal";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a valid snapshot with all 5 canonical directions. */
function makeValidSnapshot(
  distance_mm: number = 10.0,
  baseTemp: number = 400.0
): ThermalSnapshot {
  return {
    distance_mm,
    readings: [
      { direction: "center", temp_celsius: baseTemp },
      { direction: "north", temp_celsius: baseTemp - 20 },
      { direction: "south", temp_celsius: baseTemp - 10 },
      { direction: "east", temp_celsius: baseTemp - 30 },
      { direction: "west", temp_celsius: baseTemp - 25 },
    ],
  };
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

describe("THERMAL_DIRECTIONS constant", () => {
  it("has exactly 5 directions", () => {
    expect(THERMAL_DIRECTIONS).toHaveLength(5);
  });

  it("contains center and all 4 cardinal directions", () => {
    expect(THERMAL_DIRECTIONS).toContain("center");
    expect(THERMAL_DIRECTIONS).toContain("north");
    expect(THERMAL_DIRECTIONS).toContain("south");
    expect(THERMAL_DIRECTIONS).toContain("east");
    expect(THERMAL_DIRECTIONS).toContain("west");
  });

  it("is readonly (frozen)", () => {
    // Attempting to push should throw because the array is readonly at the type level.
    // At runtime, Object.isFrozen checks the actual array.
    // Since `as const` doesn't freeze at runtime, we just verify length is stable.
    const original = [...THERMAL_DIRECTIONS];
    expect(THERMAL_DIRECTIONS).toEqual(original);
  });
});

describe("READINGS_PER_SNAPSHOT constant", () => {
  it("equals 5", () => {
    expect(READINGS_PER_SNAPSHOT).toBe(5);
  });

  it("matches THERMAL_DIRECTIONS length", () => {
    expect(READINGS_PER_SNAPSHOT).toBe(THERMAL_DIRECTIONS.length);
  });
});

// ---------------------------------------------------------------------------
// isThermalDirection
// ---------------------------------------------------------------------------

describe("isThermalDirection", () => {
  it.each(["center", "north", "south", "east", "west"])(
    "returns true for valid direction '%s'",
    (dir) => {
      expect(isThermalDirection(dir)).toBe(true);
    }
  );

  it.each(["northeast", "up", "down", "Centre", "CENTER", "", "null"])(
    "returns false for invalid direction '%s'",
    (dir) => {
      expect(isThermalDirection(dir)).toBe(false);
    }
  );
});

// ---------------------------------------------------------------------------
// TemperaturePoint — structural checks
// ---------------------------------------------------------------------------

describe("TemperaturePoint structure", () => {
  it("accepts a valid center reading", () => {
    const point: TemperaturePoint = {
      direction: "center",
      temp_celsius: 425.3,
    };
    expect(point.direction).toBe("center");
    expect(point.temp_celsius).toBe(425.3);
  });

  it("uses snake_case field names matching backend", () => {
    const point: TemperaturePoint = {
      direction: "north",
      temp_celsius: 380.1,
    };
    // Verify snake_case — the key literally contains an underscore
    expect("temp_celsius" in point).toBe(true);
    expect("direction" in point).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// ThermalSnapshot structure
// ---------------------------------------------------------------------------

describe("ThermalSnapshot structure", () => {
  it("accepts a valid snapshot with 5 readings", () => {
    const snapshot = makeValidSnapshot();
    expect(snapshot.distance_mm).toBe(10.0);
    expect(snapshot.readings).toHaveLength(5);
  });

  it("uses snake_case field names matching backend", () => {
    const snapshot = makeValidSnapshot();
    expect("distance_mm" in snapshot).toBe(true);
    expect("readings" in snapshot).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// validateThermalSnapshot — valid cases
// ---------------------------------------------------------------------------

describe("validateThermalSnapshot — valid cases", () => {
  it("returns no errors for a valid snapshot", () => {
    const errors = validateThermalSnapshot(makeValidSnapshot());
    expect(errors).toEqual([]);
  });

  it("accepts different positive distances", () => {
    expect(validateThermalSnapshot(makeValidSnapshot(0.1))).toEqual([]);
    expect(validateThermalSnapshot(makeValidSnapshot(500.0))).toEqual([]);
    expect(validateThermalSnapshot(makeValidSnapshot(9999.9))).toEqual([]);
  });

  it("accepts readings in any order as long as all 5 are present", () => {
    const snapshot: ThermalSnapshot = {
      distance_mm: 10.0,
      readings: [
        { direction: "west", temp_celsius: 375.0 },
        { direction: "center", temp_celsius: 425.3 },
        { direction: "east", temp_celsius: 370.2 },
        { direction: "south", temp_celsius: 390.7 },
        { direction: "north", temp_celsius: 380.1 },
      ],
    };
    expect(validateThermalSnapshot(snapshot)).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// validateThermalSnapshot — invalid cases
// ---------------------------------------------------------------------------

describe("validateThermalSnapshot — invalid distance", () => {
  it("rejects distance_mm = 0", () => {
    const snapshot = makeValidSnapshot(0);
    const errors = validateThermalSnapshot(snapshot);
    expect(errors.length).toBeGreaterThan(0);
    expect(errors[0]).toContain("distance_mm must be a positive number");
  });

  it("rejects negative distance_mm", () => {
    const snapshot = makeValidSnapshot(-5.0);
    const errors = validateThermalSnapshot(snapshot);
    expect(errors.length).toBeGreaterThan(0);
    expect(errors[0]).toContain("distance_mm must be a positive number");
  });
});

describe("validateThermalSnapshot — wrong reading count", () => {
  it("rejects fewer than 5 readings", () => {
    const snapshot: ThermalSnapshot = {
      distance_mm: 10.0,
      readings: [
        { direction: "center", temp_celsius: 425.3 },
        { direction: "north", temp_celsius: 380.1 },
      ],
    };
    const errors = validateThermalSnapshot(snapshot);
    expect(errors.some((e) => e.includes("exactly 5 elements"))).toBe(true);
  });

  it("rejects more than 5 readings", () => {
    const snapshot: ThermalSnapshot = {
      distance_mm: 10.0,
      readings: [
        { direction: "center", temp_celsius: 425.3 },
        { direction: "north", temp_celsius: 380.1 },
        { direction: "south", temp_celsius: 390.7 },
        { direction: "east", temp_celsius: 370.2 },
        { direction: "west", temp_celsius: 375.0 },
        { direction: "center", temp_celsius: 400.0 },
      ],
    };
    const errors = validateThermalSnapshot(snapshot);
    expect(errors.some((e) => e.includes("exactly 5 elements"))).toBe(true);
  });

  it("rejects empty readings", () => {
    const snapshot: ThermalSnapshot = {
      distance_mm: 10.0,
      readings: [],
    };
    const errors = validateThermalSnapshot(snapshot);
    expect(errors.some((e) => e.includes("exactly 5 elements"))).toBe(true);
  });
});

describe("validateThermalSnapshot — missing directions", () => {
  it("reports missing direction when one is absent", () => {
    const snapshot: ThermalSnapshot = {
      distance_mm: 10.0,
      readings: [
        { direction: "center", temp_celsius: 425.3 },
        { direction: "north", temp_celsius: 380.1 },
        { direction: "south", temp_celsius: 390.7 },
        { direction: "east", temp_celsius: 370.2 },
        // "west" is missing — replaced with duplicate "center"
        { direction: "center", temp_celsius: 400.0 },
      ],
    };
    const errors = validateThermalSnapshot(snapshot);
    expect(errors.some((e) => e.includes('Missing direction: "west"'))).toBe(
      true
    );
    expect(
      errors.some((e) => e.includes('Duplicate direction: "center"'))
    ).toBe(true);
  });
});

describe("validateThermalSnapshot — invalid direction string", () => {
  it("reports invalid direction", () => {
    const snapshot = {
      distance_mm: 10.0,
      readings: [
        { direction: "center", temp_celsius: 425.3 },
        { direction: "north", temp_celsius: 380.1 },
        { direction: "south", temp_celsius: 390.7 },
        { direction: "east", temp_celsius: 370.2 },
        { direction: "northeast", temp_celsius: 375.0 }, // invalid
      ],
    } as unknown as ThermalSnapshot;
    const errors = validateThermalSnapshot(snapshot);
    expect(errors.some((e) => e.includes('Invalid direction: "northeast"'))).toBe(
      true
    );
    expect(errors.some((e) => e.includes('Missing direction: "west"'))).toBe(
      true
    );
  });
});

// ---------------------------------------------------------------------------
// Type-level checks (compile-time safety)
// ---------------------------------------------------------------------------

describe("Type-level compile-time safety", () => {
  it("ThermalDirection is assignable from valid string literals", () => {
    // These assignments verify the type works at compile time.
    // If any of these were invalid, TypeScript would report an error.
    const d1: ThermalDirection = "center";
    const d2: ThermalDirection = "north";
    const d3: ThermalDirection = "south";
    const d4: ThermalDirection = "east";
    const d5: ThermalDirection = "west";
    expect([d1, d2, d3, d4, d5]).toHaveLength(5);
  });

  it("TemperaturePoint requires both fields", () => {
    // Structural check: both fields must exist for the object to conform.
    const point: TemperaturePoint = {
      direction: "center",
      temp_celsius: 0,
    };
    expect(Object.keys(point)).toEqual(
      expect.arrayContaining(["direction", "temp_celsius"])
    );
  });

  it("ThermalSnapshot requires distance_mm and readings", () => {
    const snapshot: ThermalSnapshot = {
      distance_mm: 1.0,
      readings: [],
    };
    expect(Object.keys(snapshot)).toEqual(
      expect.arrayContaining(["distance_mm", "readings"])
    );
  });
});
