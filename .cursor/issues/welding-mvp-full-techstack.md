# Welding MVP - Tech Stack Structure Setup

**Type:** Feature  
**Priority:** High  
**Effort:** Medium  
**Status:** Planning

## TL;DR
Set up the complete file structure and skeleton for the welding MVP tech stack. Create placeholder files and components for ESP32 firmware, iPad app, frontend dashboard, backend, AI models, and data directories. Frontend components will have placeholder values, backend will have file structure only, and ESP32/iPad/AI/data will be empty placeholders for future implementation.

## Current State
- ✅ Next.js frontend dashboard exists (`my-app/`) - basic dashboard with metrics/charts
- ✅ FastAPI backend exists (`backend/`) - basic API serving dashboard data
- ❌ **ESP32 firmware** - Directory structure doesn't exist
- ❌ **iPad app** - Directory structure doesn't exist
- ❌ **Welding-specific backend** - File structure doesn't exist (needs models/features/scoring directories)
- ❌ **AI models** - Directory doesn't exist
- ❌ **Data structure** - Data directories don't exist
- ❌ **Frontend welding features** - Welding-specific components don't exist

## Expected Outcome

### Complete Directory Structure (Scaffolding Only)
```
/welding_mvp
├─ /esp32_firmware
│  ├─ main.ino              # ESP32 firmware, sensor reading
│  ├─ wifi_config.h         # WiFi / BLE credentials
│  └─ utils.h               # Sensor read helpers, timestamping
│
├─ /ipad_app
│  ├─ App.tsx               # Entry point
│  ├─ /components
│  │  ├─ SensorSync.tsx     # Checks all sensors connected
│  │  ├─ SessionRecorder.tsx # Buffer / send session JSON
│  │  └─ Dashboard.tsx      # Replay + metrics visualization
│  └─ /api
│     └─ backendClient.ts   # REST calls to backend
│
├─ /frontend_dashboard (my-app/)
│  ├─ package.json
│  ├─ next.config.js
│  ├─ /pages (or /app)
│  │  ├─ index.tsx          # Main dashboard page
│  │  └─ replay/[sessionId].tsx # Replay single session
│  ├─ /components
│  │  ├─ HeatMap.tsx         # Heat map visualization
│  │  ├─ TorchAngleGraph.tsx # Graph torch angle over time
│  │  └─ ScorePanel.tsx      # Rule-based scoring feedback
│
├─ /backend
│  ├─ main.py                # FastAPI app
│  ├─ /models
│  │  └─ session_model.py   # Pydantic models for session JSON
│  ├─ /features
│  │  └─ extractor.py       # Compute features (pressure, heat, torch angle)
│  ├─ /scoring
│  │  └─ rule_based.py       # Phase 1 scoring logic
│  └─ db_client.py          # Supabase/Postgres interface
│
├─ /ai_models
│  └─ similarity_model.py   # Phase 2 ML model prototype
│
├─ /data
│  ├─ /mock
│  │  └─ session_001.json    # Mock session data
│  └─ /features
│     └─ session_001_features.json
│
└─ README.md
```

### Scaffolding Requirements

**ESP32 Firmware:**
- ✅ Create directory structure: `esp32_firmware/`
- ✅ Create placeholder files: `main.ino`, `wifi_config.h`, `utils.h`
- ⚠️ Files will be empty/placeholder - implementation later

**iPad App:**
- ✅ Create directory structure: `ipad_app/`
- ✅ Create placeholder files: `App.tsx`, component files, API client
- ⚠️ Files will have basic structure only - implementation later

**Backend (FastAPI):**
- ✅ Create directory structure: `backend/models/`, `backend/features/`, `backend/scoring/`
- ✅ Create placeholder files: `session_model.py`, `extractor.py`, `rule_based.py`, `db_client.py`, `routes/sessions.py`
- ⚠️ Files will have basic structure/imports only - implementation later

**Frontend Dashboard:**
- ✅ Create welding components: `HeatMap.tsx`, `TorchAngleGraph.tsx`, `ScorePanel.tsx`
- ✅ Create replay page: `replay/[sessionId]/page.tsx`
- ✅ Components will have placeholder values/data - functional implementation later

**AI Models:**
- ✅ Create directory: `ai_models/`
- ✅ Create placeholder file: `similarity_model.py`
- ⚠️ File will be empty - implementation later

**Data:**
- ✅ Create directory structure: `data/mock/`, `data/features/`
- ⚠️ Directories will be empty - mock data later

## Relevant Files

### New Files to Create

**ESP32 Firmware:**
- `esp32_firmware/main.ino` - Main Arduino sketch
- `esp32_firmware/wifi_config.h` - WiFi/BLE configuration
- `esp32_firmware/utils.h` - Sensor reading utilities

**iPad App:**
- `ipad_app/App.tsx` - Main app entry
- `ipad_app/components/SensorSync.tsx` - Sensor connection component
- `ipad_app/components/SessionRecorder.tsx` - Session recording component
- `ipad_app/components/Dashboard.tsx` - Basic metrics display
- `ipad_app/api/backendClient.ts` - API client for backend

**Backend Extensions:**
- `backend/models/session_model.py` - Pydantic models for welding sessions
- `backend/features/extractor.py` - Feature extraction from raw sensor data
- `backend/scoring/rule_based.py` - Rule-based scoring logic
- `backend/db_client.py` - Database client (Supabase/Postgres)
- `backend/routes/sessions.py` - Session API routes

**Frontend Extensions:**
- `my-app/src/app/replay/[sessionId]/page.tsx` - Session replay page
- `my-app/src/components/welding/HeatMap.tsx` - Heat map visualization
- `my-app/src/components/welding/TorchAngleGraph.tsx` - Torch angle graph
- `my-app/src/components/welding/ScorePanel.tsx` - Scoring feedback panel
- `my-app/src/types/session.ts` - TypeScript types for welding sessions

**AI Models:**
- `ai_models/similarity_model.py` - ML model for session similarity

**Data:**
- `data/mock/session_001.json` - Mock welding session data
- `data/features/session_001_features.json` - Extracted features example

### Files to Modify

**Backend:**
- `backend/main.py` - Add session routes, update CORS for iPad app
- `backend/requirements.txt` - Add database client, ML libraries

**Frontend:**
- `my-app/src/app/page.tsx` - Update to show welding sessions list
- `my-app/src/lib/api.ts` - Add session API methods
- `my-app/package.json` - Add visualization libraries (D3, Recharts, etc.)

## Implementation Notes

### Scaffolding Approach

**ESP32 Firmware:**
- Create empty `.ino` file with basic Arduino structure
- Create empty header files with placeholder comments
- No actual sensor reading code yet

**iPad App:**
- Create React Native component files with basic structure
- Export placeholder components
- No actual functionality yet

**Backend:**
- Create Python files with basic imports and class/function stubs
- Add docstrings explaining what each file will do
- No actual implementation logic yet

**Frontend Dashboard:**
- Create React components with placeholder JSX
- Use mock/placeholder data for visualization
- Components render but show placeholder content

**AI Models:**
- Create empty Python file with placeholder comment
- No model code yet

**Data:**
- Create empty directories
- Add `.gitkeep` files to preserve directory structure in git

## Risks/Dependencies

**Minimal Dependencies (Scaffolding Only):**
- Node.js 18+ for frontend (already installed)
- Python 3.8+ for backend (already installed)
- No hardware needed yet (ESP32/iPad implementation later)
- No React Native setup needed yet (iPad app implementation later)

**Structure Risks:**
- File structure may need adjustment when implementing
- Component interfaces may need refinement
- Directory structure should follow best practices for each platform

## Success Criteria

**Scaffolding Phase:**
- ✅ All directory structures created
- ✅ All placeholder files created
- ✅ ESP32 firmware files exist (empty/placeholder)
- ✅ iPad app files exist (structure only)
- ✅ Backend file structure exists (stubs only)
- ✅ Frontend welding components exist (with placeholder data)
- ✅ AI models directory exists (empty)
- ✅ Data directories exist (empty)
- ✅ Frontend components render (with placeholder values)
- ✅ No build/compilation errors
- ✅ File structure follows best practices for each platform

## Implementation Steps

### Step 1: Create Directory Structure
- Create `esp32_firmware/` directory
- Create `ipad_app/` directory structure
- Create `backend/models/`, `backend/features/`, `backend/scoring/` directories
- Create `ai_models/` directory
- Create `data/mock/` and `data/features/` directories

### Step 2: ESP32 Firmware Placeholders
- Create `esp32_firmware/main.ino` (empty/placeholder)
- Create `esp32_firmware/wifi_config.h` (empty/placeholder)
- Create `esp32_firmware/utils.h` (empty/placeholder)

### Step 3: iPad App Structure
- Create `ipad_app/App.tsx` (basic React Native structure)
- Create `ipad_app/components/SensorSync.tsx` (placeholder component)
- Create `ipad_app/components/SessionRecorder.tsx` (placeholder component)
- Create `ipad_app/components/Dashboard.tsx` (placeholder component)
- Create `ipad_app/api/backendClient.ts` (placeholder API client)

### Step 4: Backend File Structure
- Create `backend/models/session_model.py` (stub with imports)
- Create `backend/features/extractor.py` (stub with imports)
- Create `backend/scoring/rule_based.py` (stub with imports)
- Create `backend/db_client.py` (stub with imports)
- Create `backend/routes/sessions.py` (stub with router)

### Step 5: Frontend Welding Components
- Create `my-app/src/app/replay/[sessionId]/page.tsx` (with placeholder)
- Create `my-app/src/components/welding/HeatMap.tsx` (with placeholder visualization)
- Create `my-app/src/components/welding/TorchAngleGraph.tsx` (with placeholder graph)
- Create `my-app/src/components/welding/ScorePanel.tsx` (with placeholder score display)
- Create `my-app/src/types/session.ts` (TypeScript types for sessions)

### Step 6: AI Models Placeholder
- Create `ai_models/similarity_model.py` (empty with comment)

### Step 7: Data Directories
- Create `data/mock/` directory (with `.gitkeep`)
- Create `data/features/` directory (with `.gitkeep`)

### Step 8: Verify Structure
- Verify all files exist
- Verify frontend components render without errors
- Verify backend files have correct imports (even if stubs)
- Verify no build/compilation errors
