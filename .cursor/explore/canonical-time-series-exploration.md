# Exploration: Canonical Time-Series Contract Implementation

## Current State Analysis

### Existing Models (To Be Replaced)

**Backend (`backend/models/session_model.py`):**
- `WeldingSession`: Simple structure with `meta`, `heat_map`, `torch_angle_deg`, `score`
- `HeatMapPoint`: 2D point with `x_mm`, `y_mm`, `intensity_norm`
- No frame-by-frame data, no thermal snapshots, no time-series structure

**Frontend (`my-app/src/types/session.ts`):**
- Matches backend structure (camelCase vs snake_case)
- Used by `ReplayPage` component (currently placeholder)

**Current Usage:**
- `backend/routes/sessions.py`: Uses `WeldingSession` (endpoints not implemented)
- `my-app/src/app/replay/[sessionId]/page.tsx`: Expects `WeldingSession` (TODO: fetch from API)
- `my-app/src/components/welding/HeatMap.tsx`: Placeholder component
- `my-app/src/components/welding/TorchAngleGraph.tsx`: Placeholder component

### New Contract Structure

**Backend Models (4 new files):**
1. `thermal.py`: `TemperaturePoint`, `ThermalSnapshot` (5-point cross pattern)
2. `frame.py`: `Frame` (100Hz sensor data + `List[ThermalSnapshot]`)
3. `session.py`: `Session` (aggregates frames + metadata)
4. `comparison.py`: `FrameDelta`, `ThermalDelta` (expert vs novice)

**Frontend Types (4 new files):**
- Same structure with TSDoc comments
- Must match backend exactly (snake_case)

---

## Data Flow Architecture

### Current Flow (Simple)
```
Backend: WeldingSession (meta + arrays)
  ↓ JSON serialization
Frontend: WeldingSession (camelCase)
  ↓ Component props
HeatMap/TorchAngleGraph (placeholder)
```

### New Flow (Time-Series)
```
Hardware Sensors (100Hz)
  ↓
Backend: Frame (every 10ms)
  ├─ Sensor data (angle, speed, volts, amps, trigger)
  └─ ThermalSnapshot[] (every 100ms, multiple distances)
      └─ TemperaturePoint[] (5 points: center + 4 cardinal)
  ↓
Session aggregates all Frames
  ↓ JSON serialization (chunked/paginated)
Frontend: Session type
  ↓ Filter by has_thermal_data
  ↓ Transform for visualization
HeatMap: distance × time → temperature grid
TorchAngleGraph: frame.t → angle_degrees
```

### API Endpoint Flow
```
GET /api/sessions/{session_id}
  ↓ Query params: ?include_thermal=true&time_range_start=0&limit=1000
  ↓ Backend filters/chunks frames
  ↓ Returns Session with frames array
  ↓ Frontend receives Session
  ↓ Transform frames → visualization data
```

---

## Component Structure & Data Flow

### High-Level Component Hierarchy

```
ReplayPage (sessionId)
  ├─ State: session (Session | null), loading, error
  ├─ useEffect: fetch session data on mount
  │   └─ API call: GET /api/sessions/{sessionId}?include_thermal=true
  │       └─ Returns: Session with frames[]
  │
  ├─ HeatMap Component
  │   ├─ Props: session.frames (filtered by has_thermal_data)
  │   ├─ Transform: frames → heatmap grid
  │   │   └─ For each thermal frame:
  │   │       └─ For each thermal_snapshot:
  │   │           └─ Extract center temp at distance_mm
  │   ├─ State: heatmapData (2D grid: distance × time → temp)
  │   └─ Render: 2D grid visualization (future: contour plot)
  │
  ├─ TorchAngleGraph Component
  │   ├─ Props: session.frames (all frames)
  │   ├─ Transform: frames → time series
  │   │   └─ Extract: frame.t → frame.angle_degrees
  │   ├─ State: angleData (time → angle)
  │   └─ Render: LineChart (time on X, angle on Y)
  │
  └─ ScorePanel Component
      └─ Uses: session.score (if exists, or calculate from frames)
```

### Data Transformation Patterns

**HeatMap Data Extraction (Pseudocode):**
```typescript
// Input: Session with frames[]
// Output: 2D grid for visualization

function extractHeatmapData(session: Session): HeatmapGrid {
  const thermalFrames = session.frames.filter(f => f.has_thermal_data);
  
  const grid: Map<number, Map<number, number>> = new Map();
  // grid[distance_mm][time_ms] = temperature
  
  thermalFrames.forEach(frame => {
    frame.thermal_snapshots.forEach(snapshot => {
      const center = snapshot.readings.find(r => r.direction === "center");
      if (center) {
        const distance = snapshot.distance_mm;
        const time = frame.t;
        const temp = center.temp_celsius;
        
        if (!grid.has(distance)) grid.set(distance, new Map());
        grid.get(distance)!.set(time, temp);
      }
    });
  });
  
  return grid; // Convert to array format for visualization library
}
```

**TorchAngleGraph Data Extraction (Pseudocode):**
```typescript
// Input: Session with frames[]
// Output: Time series array

function extractAngleData(session: Session): AngleTimeSeries {
  return session.frames.map(frame => ({
    time: frame.t,
    angle: frame.angle_degrees
  }));
  // Simple 1:1 mapping - no filtering needed
}
```

**Heat Dissipation Chart (Future):**
```typescript
// Input: Session with frames[]
// Output: Dissipation rate over time

function extractDissipationData(session: Session): DissipationSeries {
  const thermalFrames = session.frames.filter(f => f.has_thermal_data);
  
  return thermalFrames.map(frame => ({
    time: frame.t,
    dissipation: frame.heat_dissipation_rate ?? null
  }));
  // Already calculated in backend, just extract
}
```

---

## State Management Strategy

### Component-Level State (Recommended for MVP)

**ReplayPage Component:**
```typescript
// State structure
const [session, setSession] = useState<Session | null>(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);

// useEffect: Fetch on mount
useEffect(() => {
  fetchSession(params.sessionId)
    .then(setSession)
    .catch(setError)
    .finally(() => setLoading(false));
}, [params.sessionId]);

// Derived state (computed from session)
const heatmapData = useMemo(() => 
  session ? extractHeatmapData(session) : null,
  [session]
);

const angleData = useMemo(() => 
  session ? extractAngleData(session) : null,
  [session]
);
```

**Why component-level state:**
- Simple: No Redux/Zustand needed for MVP
- Session data is page-scoped (not shared across pages)
- Derived data can be computed with `useMemo`
- Easy to add loading/error states

**Future consideration:**
- If multiple components need same session → lift to context
- If caching needed → add React Query or SWR

---

## Side Effects & Data Fetching

### API Client Pattern

**New function in `my-app/src/lib/api.ts`:**
```typescript
// High-level pattern (not full implementation)

export async function fetchSession(
  sessionId: string,
  options?: {
    includeThermal?: boolean;
    timeRangeStart?: number;
    timeRangeEnd?: number;
    limit?: number;
  }
): Promise<Session> {
  const params = new URLSearchParams();
  if (options?.includeThermal) params.set('include_thermal', 'true');
  if (options?.timeRangeStart) params.set('time_range_start', String(options.timeRangeStart));
  if (options?.timeRangeEnd) params.set('time_range_end', String(options.timeRangeEnd));
  if (options?.limit) params.set('limit', String(options.limit));
  
  const url = `${API_URL}/api/sessions/${sessionId}?${params}`;
  const response = await fetch(url);
  
  if (!response.ok) throw new Error(`Failed to fetch session: ${response.statusText}`);
  
  return response.json(); // TypeScript infers Session type
}
```

### useEffect Hooks Needed

**ReplayPage:**
```typescript
// Single useEffect for initial fetch
useEffect(() => {
  fetchSession(params.sessionId, { includeThermal: true })
    .then(setSession)
    .catch(setError)
    .finally(() => setLoading(false));
}, [params.sessionId]);

// No cleanup needed (fetch completes, state updates, done)
```

**HeatMap (if lazy-loading thermal data):**
```typescript
// Future: If thermal data is huge, lazy-load on scroll/zoom
useEffect(() => {
  if (needsMoreData && session) {
    fetchSession(session.session_id, {
      includeThermal: true,
      timeRangeStart: visibleTimeRange.start,
      timeRangeEnd: visibleTimeRange.end
    }).then(appendFrames);
  }
}, [needsMoreData, visibleTimeRange]);
```

---

## Edge Cases & Error Handling

### Loading States
```typescript
// ReplayPage loading state
if (loading) {
  return <LoadingSkeleton />; // Show skeleton for all components
}

// Individual component loading (if data not ready)
if (!heatmapData) {
  return <HeatMapSkeleton />;
}
```

### Error States
```typescript
// ReplayPage error state
if (error) {
  return <ErrorDisplay message={error} retry={() => refetch()} />;
}

// Component-level error (if data malformed)
if (session && !session.frames.length) {
  return <EmptyState message="No frame data available" />;
}
```

### Empty States
```typescript
// No thermal data
if (session && !session.frames.some(f => f.has_thermal_data)) {
  return <EmptyState message="No thermal data in this session" />;
}

// Missing optional fields
const centerTemp = frame.thermal_snapshots[0]?.readings
  .find(r => r.direction === "center")?.temp_celsius ?? null;

if (centerTemp === null) {
  // Handle gracefully - skip this frame or show placeholder
}
```

### Data Validation
```typescript
// Runtime type guard (defensive programming)
function isValidSession(data: unknown): data is Session {
  return (
    typeof data === 'object' &&
    data !== null &&
    'session_id' in data &&
    'frames' in data &&
    Array.isArray(data.frames)
  );
}

// Use in fetch handler
fetchSession(id).then(data => {
  if (isValidSession(data)) {
    setSession(data);
  } else {
    setError('Invalid session data structure');
  }
});
```

---

## Implementation Approach

### File Structure

```
backend/
  models/
    thermal.py (NEW)          # TemperaturePoint, ThermalSnapshot
    frame.py (NEW)           # Frame with thermal_snapshots[]
    session.py (NEW)          # Session (replaces session_model.py)
    comparison.py (NEW)       # FrameDelta, ThermalDelta
    __init__.py (MODIFY)      # Export new models, deprecate old
    session_model.py (DEPRECATE) # Keep for migration, mark deprecated

  routes/
    sessions.py (MODIFY)      # Update endpoints to use new Session model
                              # Add chunking/pagination params

  services/ (NEW)
    thermal_service.py        # Heat dissipation calculation
    comparison_service.py      # Expert vs novice alignment

  migrations/ (NEW)
    migrate_sessions.py       # Convert old WeldingSession → new Session

my-app/src/
  types/
    thermal.ts (NEW)          # ThermalDirection, TemperaturePoint, ThermalSnapshot
    frame.ts (NEW)            # Frame interface
    session.ts (REPLACE)       # New Session interface (replace WeldingSession)
    comparison.ts (NEW)        # FrameDelta, ThermalDelta

  lib/
    api.ts (MODIFY)           # Add fetchSession() function

  components/
    welding/
      HeatMap.tsx (MODIFY)    # Transform frames → heatmap grid
      TorchAngleGraph.tsx (MODIFY) # Transform frames → angle time series
      HeatDissipationChart.tsx (NEW) # Future: dissipation visualization

  hooks/ (NEW, optional)
    useSessionData.ts         # Custom hook for session fetching + transformation
    useHeatmapData.ts         # Extract heatmap data from session
    useAngleData.ts           # Extract angle data from session

  app/
    replay/
      [sessionId]/
        page.tsx (MODIFY)     # Use new Session type, fetch from API
```

### Why This Structure?

**Backend Models Separation:**
- `thermal.py`: Isolated thermal concerns (reusable)
- `frame.py`: Single timestep logic (testable)
- `session.py`: Aggregation logic (clear responsibility)
- `comparison.py`: Comparison logic (separate from core models)

**Frontend Types Separation:**
- Matches backend structure (1:1 mapping)
- Easy to find corresponding types
- TSDoc comments provide IDE documentation

**Services Layer (Backend):**
- `thermal_service.py`: Business logic for heat dissipation (not in model)
- `comparison_service.py`: Complex alignment logic (separate from models)

**Hooks (Frontend, Optional):**
- `useSessionData`: Reusable fetch + state logic
- `useHeatmapData`: Reusable transformation logic
- **Alternative**: Keep logic in components if only used once (simpler)

### Migration Strategy

**Phase 1: Add New Models (Non-Breaking)**
- Create new models alongside old ones
- Old endpoints still work
- New endpoints use new models

**Phase 2: Update Frontend (Breaking)**
- Update types to use new Session
- Update components to handle frames[]
- Old WeldingSession data won't work

**Phase 3: Migrate Data**
- Run migration script on existing data
- Update all endpoints to use new models
- Remove deprecated models

---

## Key Implementation Decisions

### 1. Backend: Where Does Heat Dissipation Calculation Live?

**Option A: In Frame Model (Computed Property)**
```python
class Frame(BaseModel):
    # ... fields ...
    
    @computed_field
    def heat_dissipation_rate(self) -> Optional[float]:
        # Problem: Needs previous frame, can't access here
        return None  # Can't calculate without context
```
**Rejected**: Frame doesn't know about previous frame

**Option B: In Service Layer**
```python
# backend/services/thermal_service.py
def calculate_dissipation(prev_frame: Optional[Frame], curr_frame: Frame) -> Optional[float]:
    # Calculate here, store in curr_frame before saving
```
**Chosen**: Service handles business logic, models stay pure

**Option C: Pre-calculated in Backend, Stored in Frame**
```python
class Frame(BaseModel):
    heat_dissipation_rate: Optional[float] = None  # Pre-calculated
```
**Chosen**: Stored in frame for frontend convenience, calculated in service

### 2. Frontend: Component Props vs Derived State

**Option A: Pass Full Session**
```typescript
<HeatMap session={session} />
// Component extracts what it needs
```
**Chosen**: Components are self-contained, can extract their own data

**Option B: Pass Pre-Transformed Data**
```typescript
<HeatMap data={heatmapData} />
// Parent does transformation
```
**Rejected**: Duplicates transformation logic, harder to reuse components

**Option C: Custom Hook**
```typescript
const heatmapData = useHeatmapData(session);
<HeatMap data={heatmapData} />
```
**Future**: Good for reusability, but overkill for MVP

### 3. API: Chunking Strategy

**Option A: Single Endpoint with Query Params**
```python
GET /api/sessions/{id}?limit=1000&offset=0&include_thermal=true
```
**Chosen**: Simple, flexible, standard REST pattern

**Option B: Separate Endpoints**
```python
GET /api/sessions/{id}/frames
GET /api/sessions/{id}/thermal
```
**Rejected**: More endpoints to maintain, harder to keep in sync

**Option C: Streaming/WebSocket**
```python
WebSocket: stream frames as they arrive
```
**Future**: For real-time data, but overkill for MVP

---

## Questions & Ambiguities

### 1. Migration Path for Existing Data
**Question**: Should we support both old `WeldingSession` and new `Session` formats during transition?
**Clarification needed**: 
- Is there existing production data using `WeldingSession`?
- Can we migrate all data upfront, or need dual support?

### 2. Frontend Component Updates
**Question**: Should `HeatMap` and `TorchAngleGraph` be updated immediately, or keep as placeholders?
**Clarification needed**:
- Are these components actively used, or truly placeholders?
- Should we implement full visualization now, or just data transformation?

### 3. Expert/Novice Comparison UI
**Question**: Where will expert vs novice comparison be displayed?
**Clarification needed**:
- New page/route? (`/compare/expert/{id}/novice/{id}`)
- Component in ReplayPage?
- Separate comparison service/endpoint?

### 4. Mock Data Generation
**Question**: Should mock data match the new contract structure?
**Clarification needed**:
- Generate realistic 100Hz frame data (1500 frames for 15s)?
- Include thermal snapshots every 100ms?
- Multiple distances per thermal frame?

### 5. Heat Dissipation Calculation Timing
**Question**: When is heat dissipation calculated?
**Clarification needed**:
- On data ingestion (real-time)?
- On-demand when requested?
- Pre-calculated and stored?

### 6. API Response Size Limits
**Question**: What's the maximum session duration we need to support?
**Clarification needed**:
- 15 seconds = 1500 frames (manageable)
- 60 seconds = 6000 frames (needs chunking)
- 300 seconds = 30000 frames (definitely needs chunking)

### 7. Field Name Convention
**Question**: Backend uses snake_case, frontend uses camelCase - how to handle?
**Clarification needed**:
- Contract says "use snake_case consistently" - does frontend convert?
- Or frontend types use snake_case to match backend exactly?

### 8. Validation Error Handling
**Question**: What happens when Pydantic validation fails?
**Clarification needed**:
- Return 400 with error details?
- Log and return partial data?
- Strict validation (reject entire frame) vs lenient (skip invalid frames)?

---

## High-Level Mock Execution Plan

### Phase 1: Backend Models (Foundation)
1. Create `thermal.py` with `TemperaturePoint` and `ThermalSnapshot`
2. Create `frame.py` with `Frame` (include validators for thermal distances)
3. Create `session.py` with `Session` (include frame sequence validator)
4. Create `comparison.py` with delta models
5. Update `__init__.py` exports
6. Write unit tests for each model

### Phase 2: Backend Services
1. Create `thermal_service.py` with safe heat dissipation calculation
2. Create `comparison_service.py` with expert/novice alignment logic
3. Write unit tests for services

### Phase 3: Backend API Updates
1. Update `routes/sessions.py` to use new `Session` model
2. Add query params: `include_thermal`, `time_range_start`, `limit`, `offset`
3. Implement chunking logic
4. Write integration tests

### Phase 4: Frontend Types
1. Create `thermal.ts` with TSDoc
2. Create `frame.ts` with TSDoc
3. Replace `session.ts` with new `Session` interface
4. Create `comparison.ts` with TSDoc
5. Verify TypeScript compilation

### Phase 5: Frontend API Client
1. Add `fetchSession()` to `api.ts`
2. Add query param support
3. Add error handling
4. Test with mock data

### Phase 6: Frontend Components
1. Update `ReplayPage` to use new `Session` type
2. Implement `extractHeatmapData()` transformation
3. Update `HeatMap` to render heatmap grid
4. Update `TorchAngleGraph` to render angle time series
5. Add loading/error/empty states

### Phase 7: Mock Data & Testing
1. Generate comprehensive mock session data
2. Test serialization round-trip (Python → JSON → TypeScript)
3. Test with real component rendering
4. Verify edge cases (no thermal data, missing frames, etc.)

### Phase 8: Migration (If Needed)
1. Create migration script
2. Test on sample data
3. Document migration process
4. Execute migration

---

## Summary

This is a **major refactor** replacing simple aggregated data (`WeldingSession`) with a comprehensive time-series structure (`Session` with `Frame[]`). The implementation requires:

1. **Backend**: 4 new model files + services + API updates
2. **Frontend**: 4 new type files + component updates + data transformation
3. **Migration**: Path from old to new format (if existing data exists)
4. **Testing**: Comprehensive validation and serialization tests

The architecture is sound: models are separated by concern, services handle business logic, and frontend components transform data for visualization. The main complexity is handling large data volumes (chunking) and ensuring type safety across the stack.
