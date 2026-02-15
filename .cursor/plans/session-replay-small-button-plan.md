# Feature Implementation Plan: Small Button on Session Replay Page

**Overall Progress:** `0%`

## TLDR

Add a small, compact button to the session replay page metadata bar (alongside "Compare with another session" and "Hide/Show Comparison"). Button copies the session ID to clipboard on click — useful for sharing, debugging, and linking.

---

## Critical Decisions

- **Decision 1:** Button copies `sessionId` to clipboard — No API, no state changes; purely client-side. Deterministic and auditable.
- **Decision 2:** Place in metadata row with existing links/buttons — Keeps actions grouped; matches existing `flex-wrap items-center gap-3` layout.
- **Decision 3:** Use same compact styling as "Hide/Show Comparison" — `text-xs px-3 py-1` for visual consistency.
- **Decision 4:** `navigator.clipboard.writeText` — Standard Clipboard API; fails gracefully if unsupported (e.g. non-HTTPS, some browsers).

---

## Tasks

### Phase 1 — Add Small Button to Replay Page

**Goal:** User sees a small "Copy Session ID" button in the replay metadata bar; clicking it copies the session ID to clipboard.

---

- [ ] 🟥 **Step 1: Add Copy Session ID button** (non-critical — UI only, no API/state/DB)

**Subtasks:**
- [ ] 🟥 Add `<button>` in metadata bar (inside `{metadata && (...)}` block, after existing "Hide/Show Comparison" button)
- [ ] 🟥 Implement `onClick` handler: `navigator.clipboard.writeText(sessionId)` with optional visual feedback (e.g. brief "Copied!" text or aria-live)
- [ ] 🟥 Apply compact styling: `px-3 py-1 text-xs rounded-md bg-zinc-200 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-300 dark:hover:bg-zinc-700`
- [ ] 🟥 Add `type="button"` and `aria-label="Copy session ID to clipboard"`

**✓ Verification Test:**

**Action:**
- Start dev server (`npm run dev`)
- Navigate to `/replay/sess_expert_001` (or any valid session)
- Locate the metadata row below the "Session Replay: sess_expert_001" heading
- Click the "Copy Session ID" button

**Expected Result:**
- Button is visible in the metadata row between "Compare with another session" link and "Hide/Show Comparison" button
- Button has compact size (smaller than Play/Pause)
- Clicking copies `sess_expert_001` to clipboard
- Optional: brief "Copied!" or similar feedback appears; no console errors

**How to Observe:**
- **Visual:** Button appears in metadata bar; styling matches existing secondary buttons
- **Clipboard:** Paste (Ctrl/Cmd+V) in a text field → `sess_expert_001` appears
- **Console:** DevTools → Console → no errors on click
- **Accessibility:** `aria-label` present; button is focusable and keyboard-activatable

**Pass Criteria:**
- Button renders in metadata row
- Click copies session ID to clipboard (verifiable via paste)
- No console errors
- Styling consistent with "Hide/Show Comparison" button

**Common Failures & Fixes:**
- **If button doesn't render:** Ensure it's inside `{metadata && (...)}` block and JSX is valid
- **If clipboard doesn't copy:** `clipboard.writeText` requires secure context (HTTPS or localhost); check browser console for `Clipboard` errors
- **If styling looks off:** Compare `className` with existing "Hide/Show Comparison" button; ensure Tailwind classes match
- **If button overlaps or breaks layout:** Verify `flex-wrap gap-3` on parent; button should wrap naturally on narrow viewports

---

## Pre-Flight Checklist (Print & Check Each Phase)

| Phase | Dependency Check | How to Verify | Status |
|-------|------------------|---------------|--------|
| **Phase 1** | Dev server runs | `npm run dev` and open `http://localhost:3000` | ⬜ |
| | Session data exists | Navigate to `/replay/sess_expert_001` — page loads with heatmap/3D (or mock seed) | ⬜ |
| | Metadata row visible | "Weld type • duration • frames" and "Compare with another session" link visible | ⬜ |

---

## Risk Heatmap (Where You'll Get Stuck)

| Phase | Risk Level | What Could Go Wrong | How to Detect Early |
|-------|-----------|---------------------|---------------------|
| Phase 1 | 🟢 **10%** | Clipboard API blocked (non-HTTPS, strict privacy) | Test on localhost; if paste fails, check console for `Clipboard` / permission error |
| Phase 1 | 🟢 **5%** | Layout shift when adding button | Resize viewport; metadata row should wrap gracefully |

---

## Success Criteria (End-to-End Validation)

| Feature | Target Behavior | Verification Method |
|---------|----------------|---------------------|
| Small button visible | User sees "Copy Session ID" in metadata bar | **Test:** Load `/replay/sess_expert_001` → **Expect:** Button in metadata row → **Location:** Below session title |
| Copy on click | Session ID in clipboard after click | **Test:** Click button → Paste in text field → **Expect:** `sess_expert_001` → **Location:** Any text input |

---

⚠️ **Do not mark a step as 🟩 Done until its verification test passes. If blocked, mark 🟨 In Progress and document what failed.**
