# Project Context

> **Purpose:** High-level project state for AI tools. What exists, what patterns to follow, what constraints to respect.  
> **For AI:** Reference with `@CONTEXT.md` to avoid reimplementing features or violating patterns.  
> **Last Updated:** [DATE]

---

## Project Overview

**Name:** [Project Name]  
**Type:** [Web App | API | etc.]  
**Stack:** [Main technologies]  
**Stage:** [Incubation | MVP | Production]

**Purpose:** [1-2 sentences]

**Current State:**
- ✅ [Milestone 1]
- ✅ [Milestone 2]
- 🔄 [In progress]
- 📋 [Planned]

---

## Architecture

### System Pattern
[e.g., Client-Server, Jamstack, Microservices]

```
Frontend → Backend → Database → Storage
```

**Key Decisions:**
- [Decision 1]: [Why]
- [Decision 2]: [Why]

### Tech Stack

**Frontend:** [Framework], [UI lib], [State], [Viz libs]  
**Backend:** [Framework], [Language], [API style]  
**Database:** [Primary], [Cache], [ORM]  
**Infrastructure:** [Hosting], [CI/CD]

**Critical Dependencies:**
- [package@version] (~size) — [purpose]
- [package@version] — [purpose]


---

## Implemented Features

> **AI Rule:** Don't reimplement what's listed here.

### [Feature 1]: [e.g., 3D Visualization]
**Status:** ✅  
**What:** [Brief description]  
**Location:** [File/folder]  
**Pattern:** [High-level approach]  
**Integration:** [What uses it]

### [Feature 2]: [e.g., Playback System]
**Status:** ✅  
**What:** [Brief description]  
**State:** [How managed]  
**Integration:** [What syncs to it]

### [Feature 3]: [e.g., Data Processing]
**Status:** ✅  
**What:** [Brief description]  
**Utilities:** `func1()`, `func2()` in [file]

---

## Data Models

### [Model 1]: [e.g., Session]
```typescript
{ id, timestamp, frames[], metadata }
```
**Used by:** [Components/APIs]  
**Flow:** [Source → Transform → Consumer]

### [Model 2]: [e.g., Frame]
```typescript
{ timestamp_ms, sensor_data, thermal_data? }
```
**Sparse data:** [How handled, e.g., carry-forward]

---

## Patterns

> **AI Rule:** Follow these for consistency.

### [Pattern 1]: [e.g., Frame Resolution]
**Use when:** [Scenario]  
**How:** Find exact match, else nearest before timestamp, else first frame  
**Location:** `utils/[file].ts`

### [Pattern 2]: [e.g., SSR Safety]
**Use when:** Browser-only components (WebGL, Canvas)  
**How:** Dynamic import with `ssr: false`  
**Why:** Prevents Next.js SSR errors

### [Pattern 3]: [e.g., Visual Consistency]
**Use when:** Adding color-based features  
**How:** [Temperature ranges → color bands]  
**Alignment:** Matches [existing feature]

---

## Integration Points

> **AI Rule:** Use these, don't recreate.

### [Integration 1]: [e.g., Timeline State]
**What:** Shared playback timestamp  
**State:** `{ currentTimestamp, isPlaying, ... }`  
**Consumers:** [Component A], [Component B]  
**How to use:** [Brief integration steps]

### [Integration 2]: [e.g., Utilities]
**What:** Shared helper functions  
**Available:**
- `util1()` — [Purpose] — [File]
- `util2()` — [Purpose] — [File]

---

## Constraints

> **AI Rule:** Respect these, don't work around them.

### [Constraint 1]: [e.g., SSR Limitations]
**What:** WebGL/Canvas requires browser  
**Handle:** ✅ Dynamic import with `ssr: false` | ❌ Direct import  
**Affects:** [Features]

### [Constraint 2]: [e.g., Sparse Data]
**What:** [Data gaps in stream]  
**Handle:** [Strategy, e.g., carry-forward last known value]  
**Affects:** [Features]

### [Constraint 3]: [e.g., Bundle Size]
**What:** Keep feature bundles <600KB gzipped  
**Current:** [Dependency] (~500KB acceptable for demo)  
**Future:** Lazy load if production

---

## File Structure

```
app/                    # Pages, routes, layouts
  [feature]/           # Feature pages
  api/                 # API routes
components/            # React components
  [domain]/           # Domain-specific
  ui/                 # Shared UI
lib/
  utils/              # Utilities
  hooks/              # Custom hooks
types/                # TypeScript types
public/               # Static assets
.cursor/plans/        # Implementation plans
```

**Key Files:**
- [file]: [Purpose]
- [file]: [Purpose]

---

## API Contracts

### [Endpoint 1]: [GET /api/sessions/:id]
**Purpose:** [What it does]  
**Response:** `{ id, frames[], metadata }`  
**Used by:** [Components]

### [Endpoint 2]: [POST /api/...]
**Purpose:** [What it does]  
**Request:** `{ field: type }`  
**Response:** [Shape]

---

## Component APIs

### [Component1]: [ComponentName]
**Purpose:** [What it renders]  
**Props:** `angle: number, temp: number, label?: string`  
**Location:** [File]  
**Requirements:** Must use dynamic import (SSR safety)

### [Component2]: [ComponentName]
**Purpose:** [What it renders]  
**Props:** [Key props]  
**Integration:** [Dependencies]

---

## Not Implemented

> **AI Rule:** Don't assume these exist.

### [Enhancement 1]
**Status:** 💡 Idea  
**What:** [Description]  
**Why not yet:** [Reason]

### [Enhancement 2]
**Status:** 📋 Planned  
**What:** [Description]

---

## Explicitly Rejected

> **AI Rule:** Don't suggest these.

### [Rejected 1]: [Approach]
**What:** [Description]  
**Why rejected:** [Reason]  
**Alternative:** [What we did]

---

## AI Prompting Patterns

### Adding Feature
```
@CONTEXT.md — Check if exists
@LEARNING_LOG.md — Check past issues

Implement [feature] following:
- Pattern: [from CONTEXT]
- Integration: [from CONTEXT]
- Constraints: [from CONTEXT]
```

### Debugging
```
@CONTEXT.md — [relevant section]
@LEARNING_LOG.md — Similar issues

Expected: [based on CONTEXT]
Actual: [what's happening]
```

---

## Quick Checklist

Before prompting AI:
- [ ] Checked CONTEXT.md for existing implementation
- [ ] Reviewed patterns to follow
- [ ] Noted integration points
- [ ] Identified constraints
- [ ] Checked LEARNING_LOG.md

---

## Related Docs

| File | Purpose |
|------|---------|
| `LEARNING_LOG.md` | Mistakes & solutions |
| `.cursorrules` | AI config |
| `README.md` | Setup |

---

**Maintenance:** Update after features, weekly review, monthly validation.