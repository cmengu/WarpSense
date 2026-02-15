# Agent Context: Shipyard Welding MVP

**Purpose**: Industrial welding system (ESP32 → FastAPI/PostgreSQL → Next.js/TypeScript)  
**Critical**: Safety-adjacent - data integrity non-negotiable

## Core Rules (NEVER VIOLATE)

**Data Integrity**
- Append-only sensor data (never edit historical records)
- Backend calculates once (single source of truth)
- Exact replays (no interpolation/guessing)
- Explicit types/units: `timestamp_ms`, `temp_celsius` (not `temp`)
- Deterministic: same input = same output

**Hard Rules**
```
NEVER: silently fail | guess values | mutate raw data | hide units | introduce randomness
```

## Stack Patterns

**Backend (Python/FastAPI)**
- Pure stateless functions for calculations
- Pydantic models for all I/O validation
- Explicit exceptions (never return None on error)
- Verbose naming: `get_temperature_celsius()` not `get_temp()`

**Database (PostgreSQL)**
- Append-only: `sensor_readings` | Calculated: `features`, `scores`
- Alembic migrations for ALL schema changes
- Explicit queries (never `SELECT *`)

**Frontend (Next.js/TypeScript)**
- TypeScript interfaces for all API responses
- React Query for server state only
- Zod schemas match backend Pydantic
- Always display units: `420°C` not `420`

**WebGL (Check docs first!)**
- Browser limit: 8-16 contexts/tab
- Max 1-2 Canvas instances/page
- ALWAYS add context-loss handlers
- Read: `LEARNING_LOG.md`, `documentation/WEBGL_CONTEXT_LOSS.md`

## Code Examples

**Feature Extraction (Deterministic)**
```python
def extract_features(raw_data: List[SensorReading]) -> WeldingFeatures:
    """Pure function - same input → same output"""
    avg_temp = sum(r.temp_celsius for r in raw_data) / len(raw_data)
    return WeldingFeatures(avg_temp_celsius=avg_temp, ...)
```

**Error Handling**
```python
def get_temperature_celsius() -> float:
    try:
        raw = sensor.read()
        if raw is None:
            raise SensorReadError("Sensor returned None")
        return raw * CALIBRATION_FACTOR
    except Exception as e:
        logger.error(f"Temperature read failed: {e}")
        raise SensorReadError(f"Failed: {e}")
```

**Validation**
```typescript
const response = await fetch('/api/data');
const data = SensorDataSchema.parse(await response.json());
```

## Testing (100% coverage required)
- Feature extraction, scoring, validation, APIs, replay accuracy
- Must be deterministic: `assert extract(data) == extract(data)`

## Review Process
1. Flag: HIGH (integrity/safety) | MEDIUM (tests/units) | LOW (style)
2. Fix HIGH immediately, MEDIUM if time permits
3. Verify with tests

## Quick Reference

**File Structure**: `api/`, `models/`, `schemas/`, `services/`, `tests/` (backend) | `components/`, `pages/`, `lib/`, `types/` (frontend)

**Data Flow**: `ESP32 → POST /api/sensor-data → Validate → Append DB → Calculate → Return`

**MVP Constraints**: ✅ Explicit logic, redundant validation, boring code | ❌ ML models, auto-tuning, implicit behavior, abstractions

**When Stuck**: Check `LEARNING_LOG.md` → `documentation/` → `.cursor/rules/` → existing code → ask

**Mantras**: "Data integrity > speed" | "Never silently fail" | "Boring > clever" | "Same input = same output"