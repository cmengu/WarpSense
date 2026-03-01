# Issue: Fix 4 — Expert Weld Pool Temp Shows 39°C

**Type:** Bug  
**Priority:** High  
**Effort:** Small–Medium  
**Labels:** `bug` `thermal` `mock-data` `compare` `demo` `investor-facing`

---

## TL;DR

Session B shows 39°C weld pool temp in the compare view — room temperature, physically impossible during welding. Fix thermal extraction or mock generation before this reaches an investor demo.

---

## Evidence

![Session B weld pool temp 39°C](assets/weld-pool-temp-39c.png)

*(Attach screenshot to `docs/assets/weld-pool-temp-39c.png`. Anyone picking this up should see the bug immediately without reproducing.)*

---

## Current State vs Expected Outcome

### Current State
- Compare page `/compare/sess_expert_001/sess_novice_001`: Session A (expert) and Session B (novice) each show a 3D torch with "Weld pool temp" label
- One of these (Session B per report, or possibly Expert per title) displays **39°C**
- 39°C is room temperature — weld pools are 400–1500°C depending on process
- Mock data is supposed to produce realistic thermal profiles (BASE_CENTER_TEMPS ~520°C at 10mm for mild steel)

### Expected Outcome
- Weld pool temp for **both sessions** in the compare view shows realistic welding temperatures (e.g. 300–600°C range for MIG mild steel at arc-adjacent distances)
- No investor-facing moment where the displayed value contradicts basic welding physics

---

## Relevant Files

| File | Purpose |
|------|---------|
| `backend/data/mock_sessions.py` | Generates thermal snapshots for sess_expert_001, sess_novice_001; `generate_thermal_snapshots`, `BASE_CENTER_TEMPS`, `generate_frames` |
| `my-app/src/utils/frameUtils.ts` | `extractCenterTemperature`, `extractCenterTemperatureWithCarryForward` — reads `thermal_snapshots[0]` (closest = 10mm) |
| `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx` | Passes `extractCenterTemperatureWithCarryForward(sessionB.frames, currentTimestamp)` to TorchWithHeatmap3D |
| `my-app/src/components/welding/TorchWithHeatmap3D.tsx` | Displays "Weld pool temp" label with `temp.toFixed(0)°C` |

---

## Investigation Notes

1. **Source of 39°C:** Must come from actual thermal data (fallback is 450°C). Check:
   - Is `thermal_snapshots[0]` always the closest distance (10mm)? Backend may return snapshots in different order.
   - Does Session B (sess_novice_001) have sparse thermal data or thermal gap causing carry-forward from a cold frame?
   - Are we inadvertently reading a non-center direction (north/south/west) that can be much cooler?

2. **Mock physics:** Mild steel mock uses `BASE_CENTER_TEMPS[10.0]=520`, `max(20, center_temp)` clamp. At 50mm west: 95−80=15°C baseline. Heavy cooling + negative power_delta could push some readings into 30–40°C range — but we should read **10mm center** only.

3. **API / include_thermal:** Compare page fetches with `include_thermal: true`. If thermal is stripped or frames come back with empty snapshots, carry-forward would use 450°C — so 39 implies real data exists and is wrong.

4. **Session ordering:** Expert vs Novice = Session A = sess_expert_001, Session B = sess_novice_001. User report says "Session B"; title says "Expert" — could be either.

---

## Risk / Notes

- **Investor credibility:** Product vision (vision.md) stresses investor-facing demos. A 39°C weld pool undermines technical credibility.
- **Data integrity contract:** Raw data is append-only; fix is in mock generation or frontend extraction, not DB mutation.
- **Verification:** Add automated test that `extractCenterTemperatureWithCarryForward` for seeded sess_expert_001 and sess_novice_001 never returns values < 100°C at any timestamp where arc is active.

---

## Vision Alignment

From `vision.md`:
- "Technical credibility — system handles 3000-frame sessions without lag or placeholder text"
- "The test: Can they send something to someone else after the meeting? If yes: the demo worked."

A weld pool showing room temperature is a placeholder-text-class failure. Fix before investor demos.

---

## Acceptance Criteria

- [ ] Both sessions show weld pool temp > 200°C at any arc-active frame
- [ ] Compare page expert session shows 300–600°C range consistently
- [ ] `verify_aluminum_mock.py` passes with no thermal values < 100°C at arc-active frames
- [ ] Manually verified on `/compare/sess_novice_aluminium_001_001/sess_expert_aluminium_001_001`
