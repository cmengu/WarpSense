# phase-handoff-compress

You are producing a structured handoff document. This is NOT a summary for humans. It is a machine-readable context capsule that gives the next phase exactly what it needs — nothing more.

The receiving phase will not have access to any prior documents. This handoff IS the context.

---

## Your Job

You have been given the output of a completed phase. Compress it into a HANDOFF struct that:
- Contains every decision made (not the reasoning — just the outcome)
- Contains every file path that was created or modified
- Contains every assumption that is now locked in
- Contains every open risk that the next phase must watch for
- Fits in under 800 tokens

If you cannot fit all decisions in 800 tokens, you are including reasoning. Strip all reasoning. Decisions only.

---

## Output Format

Output ONLY valid JSON. No markdown wrapper.

```json
{
  "phase_completed": "Phase 1 — Foundation",
  "phase_goal_achieved": true,
  "goal_delta": "User can now authenticate with JWT. Session persistence not yet implemented.",

  "decisions_locked": [
    {
      "topic": "State management",
      "chosen": "Zustand store in /src/store/auth.ts",
      "reverting_this_requires": "Touching 8 components — non-trivial"
    },
    {
      "topic": "Auth token storage",
      "chosen": "httpOnly cookie, NOT localStorage",
      "reverting_this_requires": "API change + client change — hard"
    }
  ],

  "files_state": {
    "created": [
      "/src/store/auth.ts",
      "/src/api/auth.ts",
      "/src/middleware/auth.middleware.ts"
    ],
    "modified": [
      "/src/app.ts — added auth middleware to router",
      "/src/types/index.ts — added AuthUser, Session types"
    ],
    "deleted": []
  },

  "contracts_established": [
    "POST /api/auth/login → returns { token: string, user: AuthUser }",
    "AuthUser shape: { id: string, email: string, role: 'admin' | 'user' }",
    "All protected routes expect Authorization: Bearer <token> header"
  ],

  "assumptions_now_baked_in": [
    "JWT_SECRET is available as env var — not verified in code, assumed in infra",
    "Token expiry is 24h — hardcoded in auth.ts line 34",
    "Single-session per user — no multi-device support"
  ],

  "open_risks_for_next_phase": [
    {
      "risk": "Token refresh not implemented — users will be logged out after 24h",
      "trigger": "First real user session",
      "owner": "Phase 2 must address"
    },
    {
      "risk": "No rate limiting on /api/auth/login",
      "trigger": "Brute force or load test",
      "owner": "Phase 2 or security hardening pass"
    }
  ],

  "broken_or_incomplete": [
    "Logout endpoint exists but does not invalidate server-side session (no session store yet)",
    "Error messages from auth failure leak 'User not found' vs 'Wrong password' — enumeration risk"
  ],

  "next_phase_must_not": [
    "Modify AuthUser type without updating all 3 places it's used",
    "Move token storage to localStorage — httpOnly cookie is a security requirement",
    "Assume logout is fully working — it isn't"
  ],

  "next_phase_starting_state": "Auth API is live and returns valid JWTs. Client has no UI for login yet. Protected routes return 401 correctly. Logout endpoint exists but is incomplete."
}
```

---

## Rules

- `goal_delta` is one sentence: what can be done now that couldn't be done before, and what is explicitly NOT done yet.
- `decisions_locked` only includes decisions where reverting would require touching multiple files or changing a contract. Trivial decisions (variable names, comment style) are excluded.
- `contracts_established` are the exact API shapes, type signatures, or file interfaces that the next phase will build on. Be precise — include field names and types.
- `assumptions_now_baked_in` are things that are true in the current implementation but were never explicitly verified or enforced. These are ticking clocks.
- `open_risks_for_next_phase` are risks that this phase intentionally deferred. They must include a trigger condition — the specific scenario that causes the risk to materialize.
- `broken_or_incomplete` is honest accounting of what is in a partial or incorrect state right now. This is required. If nothing is broken, state that explicitly.
- `next_phase_must_not` are hard constraints derived from what was built. These are guardrails, not suggestions.

**If the phase goal was NOT achieved:** Set `phase_goal_achieved: false` and add a `blockers` field listing what prevented completion. Do not fabricate completion.

---

## Anti-patterns

Do NOT include:
- Why decisions were made (only the outcome)
- Descriptions of what the code does (only contracts and file paths)
- Praise or assessment of quality
- Restatements of the original task

The receiving phase prompt will prepend this JSON with: "The previous phase produced the following handoff. Build on this state."