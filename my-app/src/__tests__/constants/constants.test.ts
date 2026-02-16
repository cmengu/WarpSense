/**
 * Tests for frontend constants (Step 13B).
 * Any change here can ripple through components, services, tests, and occasionally the backend.
 *
 * Validates:
 *   - metals.ts: METAL_TYPES, METAL_TYPE_LABELS, METAL_PROPERTIES
 *   - sensors.ts: SENSOR_RANGES, SENSOR_UNITS, TEMPERATURE_RANGE_CELSIUS
 *   - validation.ts: timing, limits, thresholds, error messages, VALIDATION_RULES
 *   - Constants match backend validation rules
 */

import {
  METAL_TYPES,
  METAL_TYPE_LABELS,
  METAL_PROPERTIES,
} from "@/constants/metals";
import type { MetalType } from "@/constants/metals";
import {
  SENSOR_RANGES,
  SENSOR_UNITS,
  TEMPERATURE_RANGE_CELSIUS,
} from "@/constants/sensors";
import {
  FRAME_INTERVAL_MS,
  FRAME_INTERVAL_TOLERANCE_MS,
  THERMAL_SAMPLE_INTERVAL_MS,
  MAX_SESSION_DURATION_MS,
  MAX_FRAMES_PER_SESSION,
  SENSOR_SAMPLE_RATE_HZ,
  MIN_FRAMES_PER_REQUEST,
  MAX_FRAMES_PER_REQUEST,
  DEFAULT_PAGE_SIZE,
  MAX_PAGE_SIZE,
  MAX_AMPS_JUMP_RATIO,
  MAX_VOLTS_JUMP_RATIO,
  READINGS_PER_THERMAL_SNAPSHOT,
  THERMAL_DISTANCE_TOLERANCE_MM,
  ERROR_MESSAGES,
  VALIDATION_RULES,
} from "@/constants/validation";
import { READINGS_PER_SNAPSHOT } from "@/types/thermal";
import {
  THERMAL_MAX_TEMP,
  THERMAL_MIN_TEMP,
  THERMAL_COLOR_SENSITIVITY,
  THERMAL_ABSOLUTE_MAX,
} from "@/constants/thermal";

// ===========================================================================
// metals.ts
// ===========================================================================

describe("METAL_TYPES", () => {
  it("has at least 3 metal types", () => {
    expect(METAL_TYPES.length).toBeGreaterThanOrEqual(3);
  });

  it("includes common welding metals", () => {
    expect(METAL_TYPES).toContain("mild_steel");
    expect(METAL_TYPES).toContain("stainless_steel");
    expect(METAL_TYPES).toContain("aluminum");
  });

  it("contains no duplicates", () => {
    expect(new Set(METAL_TYPES).size).toBe(METAL_TYPES.length);
  });
});

describe("METAL_TYPE_LABELS", () => {
  it("has a label for every metal type", () => {
    for (const type of METAL_TYPES) {
      expect(METAL_TYPE_LABELS[type]).toBeTruthy();
      expect(typeof METAL_TYPE_LABELS[type]).toBe("string");
    }
  });

  it("labels are human-readable (capitalized words)", () => {
    for (const type of METAL_TYPES) {
      // Each label should start with an uppercase letter
      expect(METAL_TYPE_LABELS[type][0]).toBe(
        METAL_TYPE_LABELS[type][0].toUpperCase()
      );
    }
  });
});

describe("METAL_PROPERTIES", () => {
  it("has properties for every metal type", () => {
    for (const type of METAL_TYPES) {
      expect(METAL_PROPERTIES[type]).toBeDefined();
    }
  });

  it("melting points are positive and reasonable", () => {
    for (const type of METAL_TYPES) {
      const mp = METAL_PROPERTIES[type].melting_point_celsius;
      expect(mp).toBeGreaterThan(0);
      expect(mp).toBeLessThan(5000);
    }
  });

  it("thermal conductivity is positive", () => {
    for (const type of METAL_TYPES) {
      expect(
        METAL_PROPERTIES[type].thermal_conductivity_w_per_mk
      ).toBeGreaterThan(0);
    }
  });

  it("voltage ranges are [min, max] with min < max", () => {
    for (const type of METAL_TYPES) {
      const [min, max] = METAL_PROPERTIES[type].typical_voltage_range_volts;
      expect(min).toBeLessThan(max);
      expect(min).toBeGreaterThan(0);
    }
  });

  it("amperage ranges are [min, max] with min < max", () => {
    for (const type of METAL_TYPES) {
      const [min, max] = METAL_PROPERTIES[type].typical_amperage_range_amps;
      expect(min).toBeLessThan(max);
      expect(min).toBeGreaterThan(0);
    }
  });

  it("preheat temps are non-negative", () => {
    for (const type of METAL_TYPES) {
      expect(METAL_PROPERTIES[type].preheat_temp_celsius).toBeGreaterThanOrEqual(0);
    }
  });
});

// ===========================================================================
// sensors.ts
// ===========================================================================

describe("SENSOR_RANGES", () => {
  it("defines ranges for volts, amps, angle_degrees", () => {
    expect(SENSOR_RANGES.volts).toBeDefined();
    expect(SENSOR_RANGES.amps).toBeDefined();
    expect(SENSOR_RANGES.angle_degrees).toBeDefined();
  });

  it("each range has min < max and a unit string", () => {
    for (const [, range] of Object.entries(SENSOR_RANGES)) {
      expect(range.min).toBeLessThan(range.max);
      expect(typeof range.unit).toBe("string");
      expect(range.unit.length).toBeGreaterThan(0);
    }
  });
});

describe("SENSOR_UNITS", () => {
  it("defines units for core sensor fields", () => {
    expect(SENSOR_UNITS.volts).toBe("V");
    expect(SENSOR_UNITS.amps).toBe("A");
    expect(SENSOR_UNITS.angle_degrees).toBe("°");
    expect(SENSOR_UNITS.temp_celsius).toBe("°C");
    expect(SENSOR_UNITS.distance_mm).toBe("mm");
    expect(SENSOR_UNITS.timestamp_ms).toBe("ms");
    expect(SENSOR_UNITS.heat_dissipation_rate_celsius_per_sec).toBe("°C/s");
  });
});

describe("TEMPERATURE_RANGE_CELSIUS", () => {
  it("min is below freezing (handles cold environments)", () => {
    expect(TEMPERATURE_RANGE_CELSIUS.min).toBeLessThan(0);
  });

  it("max covers welding temperatures", () => {
    expect(TEMPERATURE_RANGE_CELSIUS.max).toBeGreaterThan(1000);
  });

  it("min < max", () => {
    expect(TEMPERATURE_RANGE_CELSIUS.min).toBeLessThan(
      TEMPERATURE_RANGE_CELSIUS.max
    );
  });
});

// ===========================================================================
// validation.ts
// ===========================================================================

describe("Frame timing constants", () => {
  it("FRAME_INTERVAL_MS is 10 (100Hz)", () => {
    expect(FRAME_INTERVAL_MS).toBe(10);
  });

  it("FRAME_INTERVAL_TOLERANCE_MS is 1", () => {
    expect(FRAME_INTERVAL_TOLERANCE_MS).toBe(1);
  });

  it("THERMAL_SAMPLE_INTERVAL_MS is 100 (5Hz)", () => {
    expect(THERMAL_SAMPLE_INTERVAL_MS).toBe(100);
  });

  it("SENSOR_SAMPLE_RATE_HZ is 100", () => {
    expect(SENSOR_SAMPLE_RATE_HZ).toBe(100);
  });

  it("frame interval and sample rate are consistent", () => {
    // 1000ms / SENSOR_SAMPLE_RATE_HZ should equal FRAME_INTERVAL_MS
    expect(1000 / SENSOR_SAMPLE_RATE_HZ).toBe(FRAME_INTERVAL_MS);
  });
});

describe("Session limits", () => {
  it("MAX_SESSION_DURATION_MS is 5 minutes", () => {
    expect(MAX_SESSION_DURATION_MS).toBe(300_000);
  });

  it("MAX_FRAMES_PER_SESSION is 30000", () => {
    expect(MAX_FRAMES_PER_SESSION).toBe(30_000);
  });

  it("max frames matches duration / interval", () => {
    expect(MAX_SESSION_DURATION_MS / FRAME_INTERVAL_MS).toBe(
      MAX_FRAMES_PER_SESSION
    );
  });
});

describe("Ingestion limits", () => {
  it("MIN_FRAMES_PER_REQUEST is 1000", () => {
    expect(MIN_FRAMES_PER_REQUEST).toBe(1000);
  });

  it("MAX_FRAMES_PER_REQUEST is 5000", () => {
    expect(MAX_FRAMES_PER_REQUEST).toBe(5000);
  });

  it("min < max", () => {
    expect(MIN_FRAMES_PER_REQUEST).toBeLessThan(MAX_FRAMES_PER_REQUEST);
  });
});

describe("Pagination limits", () => {
  it("DEFAULT_PAGE_SIZE is 1000", () => {
    expect(DEFAULT_PAGE_SIZE).toBe(1000);
  });

  it("MAX_PAGE_SIZE is 10000", () => {
    expect(MAX_PAGE_SIZE).toBe(10_000);
  });
});

describe("Sensor continuity thresholds match backend", () => {
  it("MAX_AMPS_JUMP_RATIO is 0.20 (20%)", () => {
    expect(MAX_AMPS_JUMP_RATIO).toBe(0.20);
  });

  it("MAX_VOLTS_JUMP_RATIO is 0.10 (10%)", () => {
    expect(MAX_VOLTS_JUMP_RATIO).toBe(0.10);
  });
});

describe("Thermal validation matches backend", () => {
  it("READINGS_PER_THERMAL_SNAPSHOT is 5", () => {
    expect(READINGS_PER_THERMAL_SNAPSHOT).toBe(5);
  });

  it("matches READINGS_PER_SNAPSHOT from thermal types", () => {
    expect(READINGS_PER_THERMAL_SNAPSHOT).toBe(READINGS_PER_SNAPSHOT);
  });

  it("THERMAL_DISTANCE_TOLERANCE_MM is 0.1", () => {
    expect(THERMAL_DISTANCE_TOLERANCE_MM).toBe(0.1);
  });
});

describe("ERROR_MESSAGES", () => {
  it("has messages for all common error cases", () => {
    expect(ERROR_MESSAGES.SESSION_NOT_FOUND).toBeTruthy();
    expect(ERROR_MESSAGES.SESSION_LOCKED).toBeTruthy();
    expect(ERROR_MESSAGES.SESSION_COMPLETE).toBeTruthy();
    expect(ERROR_MESSAGES.FRAMES_OUT_OF_ORDER).toBeTruthy();
    expect(ERROR_MESSAGES.DUPLICATE_TIMESTAMPS).toBeTruthy();
    expect(ERROR_MESSAGES.FRAME_GAP_DETECTED).toBeTruthy();
    expect(ERROR_MESSAGES.THERMAL_DISTANCE_MISMATCH).toBeTruthy();
    expect(ERROR_MESSAGES.AMPS_JUMP_TOO_LARGE).toBeTruthy();
    expect(ERROR_MESSAGES.VOLTS_JUMP_TOO_LARGE).toBeTruthy();
    expect(ERROR_MESSAGES.PAYLOAD_TOO_LARGE).toBeTruthy();
    expect(ERROR_MESSAGES.NETWORK_ERROR).toBeTruthy();
    expect(ERROR_MESSAGES.UNKNOWN_ERROR).toBeTruthy();
  });

  it("all messages are non-empty strings", () => {
    for (const [, message] of Object.entries(ERROR_MESSAGES)) {
      expect(typeof message).toBe("string");
      expect(message.length).toBeGreaterThan(0);
    }
  });
});

describe("thermal.ts", () => {
  it("THERMAL_MAX_TEMP is 500", () => {
    expect(THERMAL_MAX_TEMP).toBe(500);
  });

  it("THERMAL_MIN_TEMP is 0", () => {
    expect(THERMAL_MIN_TEMP).toBe(0);
  });

  it("THERMAL_COLOR_SENSITIVITY is 10", () => {
    expect(THERMAL_COLOR_SENSITIVITY).toBe(10);
  });

  it("THERMAL_ABSOLUTE_MAX is 600 (sensor/interpolation ceiling)", () => {
    expect(THERMAL_ABSOLUTE_MAX).toBe(600);
  });

  it("THERMAL_MIN_TEMP < THERMAL_MAX_TEMP < THERMAL_ABSOLUTE_MAX", () => {
    expect(THERMAL_MIN_TEMP).toBeLessThan(THERMAL_MAX_TEMP);
    expect(THERMAL_MAX_TEMP).toBeLessThan(THERMAL_ABSOLUTE_MAX);
  });
});

describe("VALIDATION_RULES summary object", () => {
  it("contains all key validation rules", () => {
    expect(VALIDATION_RULES.frame_interval_ms).toBe(FRAME_INTERVAL_MS);
    expect(VALIDATION_RULES.frame_interval_tolerance_ms).toBe(
      FRAME_INTERVAL_TOLERANCE_MS
    );
    expect(VALIDATION_RULES.thermal_sample_interval_ms).toBe(
      THERMAL_SAMPLE_INTERVAL_MS
    );
    expect(VALIDATION_RULES.max_session_duration_ms).toBe(
      MAX_SESSION_DURATION_MS
    );
    expect(VALIDATION_RULES.max_frames_per_session).toBe(
      MAX_FRAMES_PER_SESSION
    );
    expect(VALIDATION_RULES.min_frames_per_request).toBe(
      MIN_FRAMES_PER_REQUEST
    );
    expect(VALIDATION_RULES.max_frames_per_request).toBe(
      MAX_FRAMES_PER_REQUEST
    );
    expect(VALIDATION_RULES.max_page_size).toBe(MAX_PAGE_SIZE);
    expect(VALIDATION_RULES.max_amps_jump_ratio).toBe(MAX_AMPS_JUMP_RATIO);
    expect(VALIDATION_RULES.max_volts_jump_ratio).toBe(MAX_VOLTS_JUMP_RATIO);
    expect(VALIDATION_RULES.readings_per_thermal_snapshot).toBe(
      READINGS_PER_THERMAL_SNAPSHOT
    );
    expect(VALIDATION_RULES.thermal_distance_tolerance_mm).toBe(
      THERMAL_DISTANCE_TOLERANCE_MM
    );
  });
});
