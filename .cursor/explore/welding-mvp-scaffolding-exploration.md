# Welding MVP Tech Stack Scaffolding - Exploration

**Date:** 2026-02-01  
**Purpose:** Full exploration and decision-making for scaffolding the welding MVP tech stack

---

## Codebase Analysis

### Current Architecture

**Frontend (Next.js 16 App Router):**
- Uses `src/app/` directory structure (App Router)
- Client components marked with `'use client'` directive
- Clear component organization: `/components`, `/types`, `/lib`
- Uses Recharts for visualizations
- Tailwind CSS with dark mode support
- Error handling via ErrorBoundary component
- State management: React hooks (useState, useEffect)
- Pattern: Page components fetch data, pass to layout components

**Backend (FastAPI):**
- Routes organized in `/routes` directory
- Models currently in root `models.py` (will need `/models/` subdirectory)
- Pydantic models match TypeScript types exactly
- CORS configured for localhost:3000
- Pattern: Router → Model validation → Return data

**Integration Points:**
1. Frontend → Backend: `fetchDashboardData()` in `lib/api.ts` calls FastAPI
2. Component pattern: Page components fetch, layout components render
3. Type safety: TypeScript interfaces match Pydantic models

---

## High-Level Mock Execution Plan

### Data Flow (For Welding Components)

```
User navigates to /replay/[sessionId]
  ↓
page.tsx (replay/[sessionId]/page.tsx)
  - useEffect: fetch session data by ID
  - State: sessionData, loading, error
  ↓
Renders welding components:
  - HeatMap (receives sessionId prop)
  - TorchAngleGraph (receives sessionId prop)
  - ScorePanel (receives sessionId prop)
```

**Component Structure:**
```
ReplayPage component:
  - State: sessionData (null), loading (true), error (null)
  - useEffect: on mount, fetch session by ID from URL param
  - Render logic:
    * If loading: show loading skeleton
    * If error: show error message
    * If data: render HeatMap + TorchAngleGraph + ScorePanel
```

**State Management:**
- State lives in page component (similar to current `page.tsx`)
- No global state needed (scaffolding phase)
- Components receive props (sessionId only)

**Side Effects:**
- `useEffect` in replay page: fetch session data on mount
- Each welding component: fetch its own data (future implementation)
- No other side effects needed for scaffolding

**Edge Cases:**
- Loading: skeleton/spinner (match current pattern)
- Error: error message with retry (match current pattern)
- Empty data: "No session data" message
- Invalid sessionId: 404 or error state

---

## Implementation Approach

### Files to Create

```
/ (project root)
├─ esp32_firmware/ (NEW)
│  ├─ main.ino (placeholder with library comments)
│  ├─ wifi_config.h (placeholder)
│  └─ utils.h (placeholder)
│
├─ ipad_app/ (NEW - Expo managed workflow)
│  ├─ App.tsx (basic React Native structure)
│  ├─ package.json (Expo dependencies)
│  ├─ components/ (NEW)
│  │  ├─ SensorSync.tsx (placeholder export)
│  │  ├─ SessionRecorder.tsx (placeholder export)
│  │  └─ Dashboard.tsx (placeholder export)
│  └─ api/ (NEW)
│     └─ backendClient.ts (placeholder functions)
│
├─ my-app/src/ (MODIFY)
│  ├─ app/
│  │  ├─ page.tsx (MODIFY - add session list with links)
│  │  └─ replay/ (NEW)
│  │     └─ [sessionId]/ (NEW)
│  │        └─ page.tsx (NEW - placeholder replay page)
│  ├─ components/
│  │  └─ welding/ (NEW)
│  │     ├─ HeatMap.tsx (NEW - renders placeholder)
│  │     ├─ TorchAngleGraph.tsx (NEW - renders placeholder)
│  │     └─ ScorePanel.tsx (NEW - renders placeholder)
│  └─ types/
│     └─ session.ts (NEW - skeletal but honest TypeScript types)
│
├─ backend/ (MODIFY)
│  ├─ models/ (NEW)
│  │  ├─ __init__.py (NEW)
│  │  └─ session_model.py (NEW - stubs)
│  ├─ features/ (NEW)
│  │  ├─ __init__.py (NEW)
│  │  └─ extractor.py (NEW - stubs)
│  ├─ scoring/ (NEW)
│  │  ├─ __init__.py (NEW)
│  │  └─ rule_based.py (NEW - stubs)
│  ├─ db_client.py (NEW - stub)
│  └─ routes/
│     └─ sessions.py (NEW - router with 501 endpoints)
│
├─ ai_models/ (NEW)
│  └─ similarity_model.py (empty)
│
└─ data/ (NEW)
   ├─ mock/ (.gitkeep)
   └─ features/ (.gitkeep)
```

### Files to Modify

1. `backend/main.py` - Add sessions router import (active, returns 501)
2. `my-app/src/app/page.tsx` - Add session list with links to replay pages

---

## Critical Decisions & Rationale

### 1. Frontend Routing: Replay Page Access

**Decision:** ✅ **Linked from main dashboard**

**Rationale:**
- Replay is the trust-building feature, not a bonus
- Forces thinking about session identity and navigation
- URL-as-source-of-truth pattern
- Costs almost nothing to add a simple link

**MVP Implementation:**
- Main dashboard shows simple list: `Session 001 → /replay/uuid`
- No fancy filters, no pagination
- Simple, reachable, real

**Avoid:**
- ❌ Hidden or unreachable replay pages
- ❌ Hardcoded session IDs only reachable via URL typing

**Rule:** If users can't reach replay, it's not real.

---

### 2. Component Props: Full Session Data vs sessionId

**Decision:** ✅ **Pass sessionId only**

**Rationale:**
- Prevents prop-drilling hell
- Avoids stale data bugs
- Matches rule: frontend must not recompute backend values
- Keeps components future-proof when data grows

**Pattern:**
```typescript
<HeatMap sessionId={sessionId} />
<TorchAngleGraph sessionId={sessionId} />
<ScorePanel sessionId={sessionId} />
```

Each component:
- Fetches read-only data
- Validates shape
- Renders

**Later upgrade:** Can lift fetching to parent without changing component APIs

**Avoid:**
- ❌ Passing giant session objects
- ❌ Mixing derived + raw data in props

---

### 3. Backend Router: sessions.py Inclusion

**Decision:** ✅ **Import router immediately, return 501 if not implemented**

**Rationale:**
- Commented code rots
- Explicit "not implemented" endpoints are honest
- Lets frontend hit real URLs early
- URL contracts are locked early
- Prevents Cursor from inventing routes

**MVP Pattern:**
```python
@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    raise HTTPException(status_code=501, detail="Not implemented yet")
```

Then in `main.py`:
```python
app.include_router(sessions.router)
```

**Benefits:**
- URL contracts locked early
- Frontend can integrate without guessing
- Clear "not implemented" status

**Avoid:**
- ❌ Commented imports
- ❌ Fake in-memory endpoints pretending to be real

---

### 4. TypeScript Types: Full Session vs Minimal

**Decision:** ✅ **Define "skeletal but honest" session type**

**Rationale:**
- Not fake, not complete, but structural
- Forces alignment with backend schema
- Prevents string/number drift
- Lets you evolve safely

**MVP session.ts Structure:**
```typescript
export interface SessionMeta {
  sessionId: string;
  startTimestampMs: number;
  firmwareVersion: string;
}

export interface HeatMapPoint {
  x_mm: number;
  y_mm: number;
  intensity_norm: number;
}

export interface WeldingSession {
  meta: SessionMeta;
  heatMap?: HeatMapPoint[];
  torchAngleDeg?: number[];
  score?: {
    total: number;
    rules: Array<{
      ruleId: string;
      threshold: number;
      passed: boolean;
    }>;
  };
}
```

**Key Principles:**
- Optional fields are OK
- Fake fields are NOT
- Structural honesty

**Avoid:**
- ❌ `any`
- ❌ "we'll define later" blobs
- ❌ UI-only types that don't match backend intent

---

### 5. iPad App: React Native vs Expo

**Decision:** ✅ **Expo (managed workflow)**

**Rationale:**
- Faster setup
- Easier device testing
- Better defaults
- Less yak-shaving
- Perfect for MVP stage (session controller, not performance-critical)

**Dependencies to Include:**
```json
{
  "expo": "^latest",
  "react-native": "^latest",
  "expo-network": "^latest",
  "expo-device": "^latest",
  "expo-file-system": "^latest"
}
```

**When NOT to use Expo:**
- Custom native sensor drivers
- Low-level Bluetooth stacks
- Heavy native extensions
- (Not needed yet)

**Avoid:**
- ❌ Overloading package.json
- ❌ Premature native eject

---

### 6. ESP32 Firmware: Libraries & Comments

**Decision:** ✅ **Mention expected libraries in comments, don't implement yet**

**Rationale:**
- Signals intent to Cursor and humans
- Prevents random library choices later
- Costs nothing
- Aligns with cursorrules: explicit, non-binding, non-magical

**Example Comment Structure:**
```cpp
// Expected libraries (subject to change):
// - ArduinoJson (serialization)
// - Adafruit_Sensor (sensor abstraction)
// - Wire / SPI (hardware interfaces)
//
// NOTE:
// Firmware must remain deterministic.
// No dynamic allocation.
// No sensor-side interpretation.
```

**Avoid:**
- ❌ Fully empty firmware (invites guessing)
- ❌ Over-implemented placeholders
- ❌ Library imports without usage

---

## MVP Law: Lock Interfaces Early

**Core Principle:**
> Lock interfaces early. Delay implementation details. Never fake correctness.

**What This Means:**
- **Interfaces:** Define real, honest structures (TypeScript types, API endpoints, component props)
- **Implementation:** Can be placeholders/stubs/501s, but structure must be real
- **Correctness:** Don't fake data that looks real but isn't

**Applied to Scaffolding:**
- ✅ Real TypeScript types (skeletal but honest)
- ✅ Real API endpoints (return 501 if not implemented)
- ✅ Real component props (sessionId, not fake data)
- ✅ Real file structure (matches final architecture)
- ❌ Fake data that looks real
- ❌ Commented-out code that hides structure
- ❌ "We'll fix it later" shortcuts

---

## Pseudocode Examples

### Frontend Replay Page

```typescript
// my-app/src/app/replay/[sessionId]/page.tsx
'use client';

export default function ReplayPage({ params }: { params: { sessionId: string } }) {
  const [sessionData, setSessionData] = useState<WeldingSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // TODO: Fetch session data from API
    // For now: show placeholder
    setLoading(false);
  }, [params.sessionId]);

  if (loading) return <LoadingSkeleton />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <div className="replay-container">
      <h1>Session Replay: {params.sessionId}</h1>
      <HeatMap sessionId={params.sessionId} />
      <TorchAngleGraph sessionId={params.sessionId} />
      <ScorePanel sessionId={params.sessionId} />
    </div>
  );
}
```

### Frontend HeatMap Component

```typescript
// my-app/src/components/welding/HeatMap.tsx
'use client';

interface HeatMapProps {
  sessionId: string;
}

export default function HeatMap({ sessionId }: HeatMapProps) {
  // Placeholder: will fetch data in future implementation
  return (
    <div className="heat-map-container bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
      <h3 className="text-lg font-semibold mb-4">Heat Map Visualization</h3>
      <div className="placeholder-visualization text-zinc-500 dark:text-zinc-400">
        Heat map for session {sessionId} - Coming soon
      </div>
    </div>
  );
}
```

### Backend Session Router

```python
# backend/routes/sessions.py
from fastapi import APIRouter, HTTPException
from typing import List

router = APIRouter()

@router.get("/api/sessions")
async def list_sessions():
    """List all welding sessions - Not implemented yet"""
    raise HTTPException(status_code=501, detail="Not implemented yet")

@router.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a specific welding session - Not implemented yet"""
    raise HTTPException(status_code=501, detail="Not implemented yet")

@router.get("/api/sessions/{session_id}/features")
async def get_session_features(session_id: str):
    """Get extracted features for a session - Not implemented yet"""
    raise HTTPException(status_code=501, detail="Not implemented yet")

@router.get("/api/sessions/{session_id}/score")
async def get_session_score(session_id: str):
    """Get scoring for a session - Not implemented yet"""
    raise HTTPException(status_code=501, detail="Not implemented yet")
```

### Backend Session Model

```python
# backend/models/session_model.py
"""
Pydantic models for welding session data structures.
Will match TypeScript interfaces for type safety.
"""

from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class SessionMeta(BaseModel):
    """Session metadata"""
    session_id: str
    start_timestamp_ms: int
    firmware_version: str

class HeatMapPoint(BaseModel):
    """Heat map data point"""
    x_mm: float
    y_mm: float
    intensity_norm: float

class ScoreRule(BaseModel):
    """Individual scoring rule result"""
    rule_id: str
    threshold: float
    passed: bool

class SessionScore(BaseModel):
    """Session scoring result"""
    total: int
    rules: List[ScoreRule]

class WeldingSession(BaseModel):
    """Complete welding session model"""
    meta: SessionMeta
    heat_map: Optional[List[HeatMapPoint]] = None
    torch_angle_deg: Optional[List[float]] = None
    score: Optional[SessionScore] = None
```

### ESP32 Firmware Placeholder

```cpp
// esp32_firmware/main.ino
/*
 * ESP32 Welding Sensor Firmware
 * 
 * Expected libraries (subject to change):
 * - ArduinoJson (serialization)
 * - Adafruit_Sensor (sensor abstraction)
 * - Wire / SPI (hardware interfaces)
 *
 * NOTE:
 * Firmware must remain deterministic.
 * No dynamic allocation.
 * No sensor-side interpretation.
 */

void setup() {
  // TODO: Initialize sensors and WiFi/BLE
}

void loop() {
  // TODO: Read sensors, timestamp, buffer, transmit
}
```

---

## Implementation Checklist

### Step 1: Root Directory Structure
- [ ] Create `esp32_firmware/` directory
- [ ] Create `ipad_app/` directory with subdirectories
- [ ] Create `ai_models/` directory
- [ ] Create `data/` directory with subdirectories
- [ ] Add `.gitkeep` files to empty directories

### Step 2: ESP32 Firmware
- [ ] Create `main.ino` with library comments
- [ ] Create `wifi_config.h` placeholder
- [ ] Create `utils.h` placeholder

### Step 3: iPad App (Expo)
- [ ] Create `App.tsx` with basic React Native structure
- [ ] Create `package.json` with Expo dependencies
- [ ] Create component placeholders
- [ ] Create API client placeholder

### Step 4: Backend Structure
- [ ] Create `models/`, `features/`, `scoring/` directories with `__init__.py`
- [ ] Create `session_model.py` with skeletal Pydantic models
- [ ] Create `extractor.py` with function stubs
- [ ] Create `rule_based.py` with function stubs
- [ ] Create `db_client.py` stub
- [ ] Create `sessions.py` router with 501 endpoints
- [ ] Update `main.py` to include sessions router

### Step 5: Frontend Welding Components
- [ ] Create `welding/` component directory
- [ ] Create `HeatMap.tsx` with placeholder
- [ ] Create `TorchAngleGraph.tsx` with placeholder
- [ ] Create `ScorePanel.tsx` with placeholder
- [ ] Create `session.ts` with skeletal TypeScript types
- [ ] Create `replay/[sessionId]/page.tsx` with placeholder
- [ ] Update main `page.tsx` to add session list with links

### Step 6: AI Models & Data
- [ ] Create `ai_models/similarity_model.py` (empty)
- [ ] Create `data/mock/.gitkeep`
- [ ] Create `data/features/.gitkeep`

### Step 7: Verification
- [ ] Verify all directories exist
- [ ] Verify all files exist
- [ ] Verify frontend components compile without errors
- [ ] Verify backend files have correct imports (no import errors)
- [ ] Test that frontend welding components render
- [ ] Test that replay page is accessible from main dashboard
- [ ] Test that backend returns 501 for unimplemented endpoints

---

## Summary

**Current State:**
- Next.js 16 App Router with clear component patterns
- FastAPI backend with route organization
- Type-safe integration between frontend and backend

**Scaffolding Approach:**
- Create complete file structure
- Placeholder components that render (with placeholder content)
- Stub backend files that compile (with 501 endpoints)
- Real TypeScript types (skeletal but honest)
- Real API endpoints (return 501 if not implemented)

**Integration:**
- Follows existing patterns (component structure, API client, error handling)
- No breaking changes (new directories/files only)
- Ready for incremental implementation

**Key Principle:**
> Lock interfaces early. Delay implementation details. Never fake correctness.
