# Plan: Thermal Gradient — Blue/Purple → Green/Orange/Red

**Overall Progress:** `100%`

## TL;DR

Replace the WarpSense blue→purple thermal gradient with green→orange→red in three places: the fragment shader (8 anchor colors), and `getWeldPoolColor` in TorchViz3D and TorchWithHeatmap3D. Zero API/logic changes. Tests pass unchanged. Visual verification on `/dev/torch-viz`.

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Before stopping: output full current contents of every file modified in this step. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) exact state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| Exact hex for getWeldPoolColor cold/mid/hot/hotEnd | Hex values matching shader gradient | Issue + shader anchor colors | Step 2, 3 | ✅ Derived from issue spec |

**Resolved values for getWeldPoolColor (derived from issue shader anchors):**
- cold (green): `0x22c55e` — matches anchorCol[1] green
- mid (orange): `0xf97316` — orange
- hot (red): `0xef4444` — red
- hotEnd (replaces white): `0xfa0505` — bright red, matches anchorCol[7]

---

## Pre-Flight — Run Before Any Code Changes

```
Read and capture:
1. heatmapFragment.glsl.ts: anchorCol[0] through anchorCol[7] — exact vec3 values (lines 30–37)
2. TorchViz3D.tsx: getWeldPoolColor signature and cold/mid/hot/white hex (lines 46–54)
3. TorchWithHeatmap3D.tsx: getWeldPoolColor — same (lines 79–88)
4. Run: cd my-app && npm test -- --testPathPattern="heatmapShaders|TorchViz|TorchWithHeatmap" --passWithNoTests 2>/dev/null | tail -5
5. Run: wc -l my-app/src/components/welding/shaders/heatmapFragment.glsl.ts my-app/src/components/welding/TorchViz3D.tsx my-app/src/components/welding/TorchWithHeatmap3D.tsx

Do not change anything. Show full output.
```

**Baseline Snapshot (agent fills during pre-flight):**
```
Test count (relevant tests): ____
Line count heatmapFragment.glsl.ts: ____
Line count TorchViz3D.tsx: ____
Line count TorchWithHeatmap3D.tsx: ____
```

**Pre-flight checks:**
- [ ] `anchorCol[0]` through `anchorCol[7]` exist in heatmapFragment.glsl.ts
- [ ] `getWeldPoolColor` exists in TorchViz3D.tsx (exactly 1 match)
- [ ] `getWeldPoolColor` exists in TorchWithHeatmap3D.tsx (exactly 1 match)
- [ ] heatmapShaders.test.ts passes

---

## Steps Analysis

- Step 1 (shader anchors) — Non-critical — verification only — Idempotent: Yes
- Step 2 (TorchViz3D getWeldPoolColor) — Non-critical — verification only — Idempotent: Yes
- Step 3 (TorchWithHeatmap3D getWeldPoolColor) — Non-critical — verification only — Idempotent: Yes

---

## Tasks

### Phase 1 — Thermal Gradient Update

**Goal:** Thermal plate and weld pool use green→orange→red gradient; all tests pass.

---

- [x] 🟩 **Step 1: Replace fragment shader anchor colors** — *Non-critical*

  **Idempotent:** Yes — replacing same block again yields same result.

  **Pre-Read Gate:**
  - `grep -n "anchorCol\[0\] = vec3" my-app/src/components/welding/shaders/heatmapFragment.glsl.ts` → exactly 1 match
  - `grep -n "anchorCol\[7\] = vec3" my-app/src/components/welding/shaders/heatmapFragment.glsl.ts` → exactly 1 match

  **Anchor Uniqueness:** The block `anchorCol[0] = vec3(0.12, 0.23, 0.54);` through `anchorCol[7] = vec3(...)` appears exactly once. Replace entire block.

  **Replace:**

  In `my-app/src/components/welding/shaders/heatmapFragment.glsl.ts`, replace:

  ```glsl
  vec3 anchorCol[8];
  anchorCol[0] = vec3(0.12, 0.23, 0.54);
  anchorCol[1] = vec3(0.15, 0.39, 0.92);
  anchorCol[2] = vec3(0.31, 0.27, 0.90);
  anchorCol[3] = vec3(0.39, 0.40, 0.95);
  anchorCol[4] = vec3(0.49, 0.23, 0.93);
  anchorCol[5] = vec3(0.55, 0.36, 0.96);
  anchorCol[6] = vec3(0.66, 0.33, 0.97);
  anchorCol[7] = vec3(0.66, 0.33, 0.97);
  ```

  **With:**

  ```glsl
  vec3 anchorCol[8];
  anchorCol[0] = vec3(0.55, 0.55, 0.55);  // cool gray (ambient)
  anchorCol[1] = vec3(0.18, 0.72, 0.38);  // green (cold weld)
  anchorCol[2] = vec3(0.40, 0.78, 0.22);  // yellow-green
  anchorCol[3] = vec3(0.85, 0.75, 0.10);  // yellow
  anchorCol[4] = vec3(0.95, 0.55, 0.05);  // orange
  anchorCol[5] = vec3(0.95, 0.30, 0.05);  // orange-red
  anchorCol[6] = vec3(0.85, 0.10, 0.05);  // red
  anchorCol[7] = vec3(0.98, 0.05, 0.05);  // hot red
  ```

  **Also update the file comment (lines 4–6):** Change "WarpSense theme: 8 anchor colors, blue (cold) → purple (hot)" to "8 anchor colors, green (cold) → orange → red (hot). IR-style thermal."

  **Verification:**
  - Type: Unit
  - Action: `cd my-app && npm test -- --testPathPattern="heatmapShaders" --passWithNoTests`
  - Expected: All heatmap shader tests pass
  - Pass: `heatmapShaders.test.ts` passes
  - Fail: Shader syntax error → check GLSL for typos

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/welding/shaders/heatmapFragment.glsl.ts
  git commit -m "thermal gradient: replace shader anchor colors with green-orange-red"
  ```

---

- [x] 🟩 **Step 2: Update getWeldPoolColor in TorchViz3D** — *Non-critical*

  **Idempotent:** Yes — same replacement is idempotent.

  **Pre-Read Gate:**
  - `grep -n "function getWeldPoolColor" my-app/src/components/welding/TorchViz3D.tsx` → exactly 1 match
  - `grep -n "0x1e3a8a" my-app/src/components/welding/TorchViz3D.tsx` → exactly 1 match (cold)

  **Replace:**

  In `my-app/src/components/welding/TorchViz3D.tsx`, replace:

  ```typescript
  /** Weld pool color: cold blue → purple → white. WarpSense theme. */
  function getWeldPoolColor(temp: number): THREE.Color {
    const cold = new THREE.Color(0x1e3a8a);
    const mid = new THREE.Color(0x6366f1);
    const hot = new THREE.Color(0xa855f7);
    const white = new THREE.Color(0xf3e8ff);
    if (temp < 200) return new THREE.Color().lerpColors(cold, mid, temp / 200);
    if (temp < 400) return new THREE.Color().lerpColors(mid, hot, (temp - 200) / 200);
    return new THREE.Color().lerpColors(hot, white, Math.min((temp - 400) / 150, 1));
  }
  ```

  **With:**

  ```typescript
  /** Weld pool color: cold green → orange → red. IR-style thermal. */
  function getWeldPoolColor(temp: number): THREE.Color {
    const cold = new THREE.Color(0x22c55e);
    const mid = new THREE.Color(0xf97316);
    const hot = new THREE.Color(0xef4444);
    const hotEnd = new THREE.Color(0xfa0505);
    if (temp < 200) return new THREE.Color().lerpColors(cold, mid, temp / 200);
    if (temp < 400) return new THREE.Color().lerpColors(mid, hot, (temp - 200) / 200);
    return new THREE.Color().lerpColors(hot, hotEnd, Math.min((temp - 400) / 150, 1));
  }
  ```

  **Verification:**
  - Type: Unit
  - Action: `cd my-app && npm test -- --testPathPattern="TorchViz3D" --passWithNoTests`
  - Expected: TorchViz3D tests pass (they mock Canvas; no color assertion)
  - Pass: Tests pass
  - Fail: Import/type error → check THREE.Color usage

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/welding/TorchViz3D.tsx
  git commit -m "thermal gradient: getWeldPoolColor green-orange-red in TorchViz3D"
  ```

---

- [x] 🟩 **Step 3: Update getWeldPoolColor in TorchWithHeatmap3D** — *Non-critical*

  **Idempotent:** Yes — same replacement is idempotent.

  **Pre-Read Gate:**
  - `grep -n "function getWeldPoolColor" my-app/src/components/welding/TorchWithHeatmap3D.tsx` → exactly 1 match
  - `grep -n "0x1e3a8a" my-app/src/components/welding/TorchWithHeatmap3D.tsx` → exactly 1 match

  **Replace:**

  In `my-app/src/components/welding/TorchWithHeatmap3D.tsx`, replace:

  ```typescript
  /** Weld pool color: cold blue → purple → white. WarpSense theme. */
  function getWeldPoolColor(temp: number): THREE.Color {
    const cold = new THREE.Color(0x1e3a8a);
    const mid = new THREE.Color(0x6366f1);
    const hot = new THREE.Color(0xa855f7);
    const white = new THREE.Color(0xf3e8ff);
    if (temp < 200) return new THREE.Color().lerpColors(cold, mid, temp / 200);
    if (temp < 400) return new THREE.Color().lerpColors(mid, hot, (temp - 200) / 200);
    return new THREE.Color().lerpColors(hot, white, Math.min((temp - 400) / 150, 1));
  }
  ```

  **With:**

  ```typescript
  /** Weld pool color: cold green → orange → red. IR-style thermal. */
  function getWeldPoolColor(temp: number): THREE.Color {
    const cold = new THREE.Color(0x22c55e);
    const mid = new THREE.Color(0xf97316);
    const hot = new THREE.Color(0xef4444);
    const hotEnd = new THREE.Color(0xfa0505);
    if (temp < 200) return new THREE.Color().lerpColors(cold, mid, temp / 200);
    if (temp < 400) return new THREE.Color().lerpColors(mid, hot, (temp - 200) / 200);
    return new THREE.Color().lerpColors(hot, hotEnd, Math.min((temp - 400) / 150, 1));
  }
  ```

  **Verification:**
  - Type: Unit
  - Action: `cd my-app && npm test -- --testPathPattern="TorchWithHeatmap3D" --passWithNoTests`
  - Expected: TorchWithHeatmap3D tests pass
  - Pass: Tests pass
  - Fail: Import/type error → check THREE.Color usage

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/welding/TorchWithHeatmap3D.tsx
  git commit -m "thermal gradient: getWeldPoolColor green-orange-red in TorchWithHeatmap3D"
  ```

---

## Regression Guard

**Systems at risk:** Thermal 3D visualization (shader + weld pool)

**Regression verification:**

| System | Pre-change | Post-change |
|--------|------------|-------------|
| heatmapShaders.test | ShaderMaterial constructs | Same — no RGB assertions |
| TorchViz3D / TorchWithHeatmap3D tests | Mock Canvas, pass | Same — no color assertions |
| Full test suite | Baseline count | `npm test` — count ≥ baseline |

**Test count:** Run `cd my-app && npm test 2>&1 | grep -E "Tests:.*passed"` — must not decrease from pre-flight.

---

## Rollback Procedure

```bash
git revert HEAD~3..HEAD   # if all 3 commits in sequence
# or individually:
git revert <commit-step3>
git revert <commit-step2>
git revert <commit-step1>
```

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| Shader anchors | 8 new vec3 values | `grep "0.18, 0.72, 0.38" heatmapFragment.glsl.ts` matches |
| TorchViz3D getWeldPoolColor | green/orange/red hex | `grep "0x22c55e" TorchViz3D.tsx` matches |
| TorchWithHeatmap3D getWeldPoolColor | same | `grep "0x22c55e" TorchWithHeatmap3D.tsx` matches |
| Tests | All pass | `npm test` — no new failures |
| Visual | Gradient consistent | Manual: /dev/torch-viz, /demo |

---

**Reference:** [docs/ISSUE_THERMAL_GRADIENT_GREEN_ORANGE_RED.md](docs/ISSUE_THERMAL_GRADIENT_GREEN_ORANGE_RED.md)
