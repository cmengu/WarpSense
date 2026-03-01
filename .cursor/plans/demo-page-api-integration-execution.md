Demo Page — Execution Plan (Iteration 3, Code-Complete)
Route: my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx
Landing: my-app/src/app/demo/page.tsx — redirects to default pair
Access: http://localhost:3000/demo → redirects to /demo/sess_novice_aluminium_001_001/sess_expert_aluminium_001_001
Direct: http://localhost:3000/demo/sess_a/sess_b for arbitrary pairs.

API Linking (Structural)
- fetchSession(sessionId) → GET {API_BASE_URL}/api/sessions/{sessionId}. Backend: sessions_router prefix /api, route /sessions/{session_id}. Full path: /api/sessions/{session_id}.
- fetchSessionAlerts(sessionId) → GET {API_BASE_URL}/api/sessions/{sessionId}/alerts. Backend route exists.
- Session response includes score_total (from session_model), frames (array of frame_data dicts). Frame frame_data includes heat_input_kj_per_mm when backend stores it (mock_sessions sets it).

Data Collection Flow (Structural)
1. Fetch: Promise.all([fetchSession(A), fetchSession(B)]) → setSessionA, setSessionB. Then Promise.allSettled([fetchSessionAlerts(A), fetchSessionAlerts(B)]) → setAlertsA/B or setAlertsErrorA/B.
2. Comparison: useSessionComparison(sessionA, sessionB) — requires Session objects, not IDs. Returns deltas at shared timestamps only.
3. Timeline: firstTimestamp = deltas[0].timestamp_ms, lastTimestamp = deltas[last].timestamp_ms. currentTimestamp drives playback, scrub, alert seek.
4. Sparkline history: useMemo (not useEffect+useState) — compute from comparison.deltas. Filter deltas where timestamp_ms <= currentTimestamp, slice(-MAX_HIST), lookup frame A and B per timestamp. Avoids 6 setState/100ms thrashing during playback.
5. Current values: getFrameAtTimestamp(session.frames, currentTimestamp) — single frame per session.
6. Alerts: visibleAlertsA = alertsA.filter(a => a.timestamp_ms <= floorTs). Each session's alerts in its own column.

Agent Failure Protocol

Verification command fails → read full error output.
Cause is unambiguous → ONE targeted fix → re-run same command.
Still failing → STOP. Output full file contents + (a) command, (b) full error verbatim, (c) fix attempted, (d) why blocked.
Never attempt a second fix without human instruction.
Never modify files not named in the current step.


Critical Decisions (Final)
DecisionValueWQI sourcesession.score_total ?? "--". No fetchScore.Correction statusOmitted entirely. Severity badge + message only.BeadDiffStatic canvas placeholder. No real data. No center temps.Alert layoutTwo columns inside right panel. Session A left, Session B right.Alert seeksetCurrentTimestamp(alert.timestamp_ms) + setIsPlaying(false). Shared timeline.History arraysuseMemo (not useEffect+useState) — avoids 6 setState per playback tick. Built from comparison.deltas only. For deltas with timestamp_ms <= currentTimestamp, slice last MAX_HIST, lookup frame A and B at each timestamp. NOT per-session independent filter.PlaybacksetInterval with FRAME_INTERVAL_MS / playbackSpeed. Copy exactly from compare page.Current frame valuesgetFrameAtTimestamp — single frame for "Current Values" panel only.

Pre-Flight — Run Before Any Code Changes
bashgrep -n "heat_input_kj_per_mm" my-app/src/types/frame.ts
# Expected: 0 matches (confirms Step 1 is needed)

grep -n "^  [a-z_]" my-app/src/types/session.ts | head -35
# Reconcile baseSession: every non-optional field (no ?) must be present. Required: session_id, operator_id, start_time, weld_type, thermal_sample_interval_ms, thermal_directions, thermal_distance_interval_mm, sensor_sample_rate_hz, frames, status, frame_count, expected_frame_count, last_successful_frame_index, validation_errors, completed_at.

grep -n "export function\|export default\|export const" my-app/src/hooks/useSessionComparison.ts
# Capture exact export name and signature

grep -n "FRAME_INTERVAL_MS" my-app/src/constants/validation.ts
# Confirm export exists and value

grep -rn "logWarn" my-app/src/lib/logger.ts | head -3
# Confirm logWarn export exists

cd my-app && npm test -- --testPathIgnorePatterns=e2e --passWithNoTests 2>&1 | tail -5
# Capture baseline test count

wc -l my-app/src/types/frame.ts

grep -n "sessions_router\|/sessions/\|/alerts" backend/main.py backend/routes/sessions.py | head -10
# Confirm backend mounts sessions at /api and has /sessions/{id} and /sessions/{id}/alerts
```

**Agent fills baseline:**
```
heat_input_kj_per_mm in frame.ts: __ matches (expect 0)
Session required fields (from grep): __ (list for Step 3 baseSession reconciliation)
FRAME_INTERVAL_MS value: __
logWarn export confirmed: yes/no
Baseline test count: __
frame.ts line count: __

Step 1 — Add heat_input_kj_per_mm to Frame type
File: my-app/src/types/frame.ts
Idempotent: Yes.
Pre-read:
bashgrep -n "travel_speed_mm_per_min" my-app/src/types/frame.ts
# Must return exactly 1 match. Insert new field on the line immediately after.
Insert after travel_speed_mm_per_min line:
ts/**
 * Heat input in kJ/mm. Backend computes: (Amps × Volts × 60) / (travel_speed_mm_per_min × 1000).
 * Optional — older sessions may lack it. Chart omits null points; never plots 0 for null.
 */
heat_input_kj_per_mm?: number | null;
Verification:
bashgrep -c "heat_input_kj_per_mm" my-app/src/types/frame.ts
# Must return 1

cd my-app && npm test -- src/__tests__ 2>&1 | tail -5
# No new failures
Git: git add my-app/src/types/frame.ts && git commit -m "step 1: add heat_input_kj_per_mm to Frame type"

Step 2 — Create demo page
Files to create:

my-app/src/app/demo/page.tsx — landing page: redirects to default pair (see below)
my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx — full implementation below
my-app/src/__tests__/app/demo/page.test.tsx — empty describe block (Step 3 adds tests)

Create my-app/src/app/demo/page.tsx first:
tsx'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

const DEFAULT_SESSION_A = 'sess_novice_aluminium_001_001';
const DEFAULT_SESSION_B = 'sess_expert_aluminium_001_001';

export default function DemoLandingPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace(`/demo/${DEFAULT_SESSION_A}/${DEFAULT_SESSION_B}`);
  }, [router]);
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#090c10', color: '#dce8f0' }}>
      <div>Redirecting to demo...</div>
    </div>
  );
}

Create my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx with exactly this content:
tsx'use client';

import { Suspense, use, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { fetchSession, fetchSessionAlerts, type AlertPayload } from '@/lib/api';
import { getRuleLabel } from '@/lib/alert-labels';
import { logWarn } from '@/lib/logger';
import { FRAME_INTERVAL_MS } from '@/constants/validation';
import { useSessionComparison } from '@/hooks/useSessionComparison';
import { getFrameAtTimestamp, extractCenterTemperatureWithCarryForward } from '@/utils/frameUtils';
import type { Session } from '@/types/session';

// ─── DESIGN TOKENS ────────────────────────────────────────────────────────────
const C = {
  bg:          '#090c10',
  surface:     '#0d1117',
  border:      'rgba(255,255,255,0.07)',
  borderBright:'rgba(255,255,255,0.14)',
  text:        '#dce8f0',
  textDim:     'rgba(180,200,215,0.38)',
  novice:      '#ff4545',
  expert:      '#00e5a0',
  specBand:    'rgba(255,255,255,0.04)',
  white:       '#f0f6ff',
  amber:       '#ffb020',
};
const FONT_LABEL = "'Syne', sans-serif";
const FONT_DATA  = "'DM Mono', monospace";
const MAX_HIST   = 60;

// ─── SPARKLINE ────────────────────────────────────────────────────────────────
// Identical visual to investor demo. Accepts pre-built history arrays — no interpolation.
function Sparkline({
  noviceHistory,
  expertHistory,
  specMin,
  specMax,
  dataMin,
  dataMax,
  label,
  unit,
}: {
  noviceHistory: number[];
  expertHistory: number[];
  specMin: number;
  specMax: number;
  dataMin: number;
  dataMax: number;
  label: string;
  unit: string;
}) {
  const W = 100, H = 52;
  const toY = (v: number) => H - ((v - dataMin) / (dataMax - dataMin)) * H;
  const toX = (i: number, len: number) => (i / (len - 1)) * W;
  const pathOf = (hist: number[]) => {
    if (hist.length < 2) return '';
    return hist
      .map((v, i) => `${i === 0 ? 'M' : 'L'} ${toX(i, hist.length).toFixed(1)} ${toY(v).toFixed(1)}`)
      .join(' ');
  };
  const specY1 = toY(specMax);
  const specY2 = toY(specMin);
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
        <span style={{ fontFamily: FONT_LABEL, fontSize: 9, letterSpacing: '0.28em', color: C.textDim, textTransform: 'uppercase' }}>{label}</span>
        <span style={{ fontFamily: FONT_DATA, fontSize: 9, color: C.textDim }}>{unit}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} style={{ display: 'block', overflow: 'visible' }}>
        <rect x={0} y={Math.min(specY1, specY2)} width={W} height={Math.abs(specY2 - specY1)} fill={C.specBand} />
        <line x1={0} y1={specY1} x2={W} y2={specY1} stroke="rgba(255,255,255,0.1)" strokeWidth={0.5} strokeDasharray="2,2" />
        {expertHistory.length > 1 && <path d={pathOf(expertHistory)} fill="none" stroke={C.expert} strokeWidth={1} opacity={0.7} />}
        {noviceHistory.length > 1 && <path d={pathOf(noviceHistory)} fill="none" stroke={C.novice} strokeWidth={1} opacity={0.85} />}
      </svg>
      <div style={{ display: 'flex', gap: 12, marginTop: 4 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 12, height: 1, background: C.novice }} />
          <span style={{ fontFamily: FONT_DATA, fontSize: 7.5, color: C.textDim }}>A</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 12, height: 1, background: C.expert }} />
          <span style={{ fontFamily: FONT_DATA, fontSize: 7.5, color: C.textDim }}>B</span>
        </div>
      </div>
    </div>
  );
}

// ─── BEAD DIFF — STATIC PLACEHOLDER ──────────────────────────────────────────
// TODO: wire to real bead-width derivation when API exists.
// No dynamic data. No extractCenterTemperatureWithCarryForward here.
function BeadDiffPlaceholder() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const dpr = window.devicePixelRatio ?? 1;
    const W = canvas.width  = canvas.offsetWidth  * dpr;
    const H = canvas.height = canvas.offsetHeight * dpr;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const cx = W / 2, cy = H / 2;
    const R  = Math.min(W, H) / 2 - 2;
    ctx.clearRect(0, 0, W, H);
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, R, 0, Math.PI * 2);
    ctx.clip();
    ctx.fillStyle = '#07090d';
    ctx.fillRect(0, 0, W, H);
    // Grid
    ctx.strokeStyle = 'rgba(255,255,255,0.03)';
    ctx.lineWidth = 0.8;
    for (let x = 0; x < W; x += W / 10) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (let y = 0; y < H; y += H / 10) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
    // Label
    ctx.fillStyle = 'rgba(180,200,215,0.2)';
    ctx.font = `${R * 0.055}px DM Mono`;
    ctx.textAlign = 'center';
    ctx.fillText('BEAD PROFILE — DERIVED', cx, cy - 8);
    ctx.fillText('(not sensor-measured)', cx, cy + 10);
    ctx.restore();
    // Rim
    ctx.strokeStyle = 'rgba(255,255,255,0.09)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(cx, cy, R - 0.5, 0, Math.PI * 2);
    ctx.stroke();
  }, []);
  return <canvas ref={ref} style={{ width: '100%', height: '100%', display: 'block', borderRadius: '50%' }} />;
}

// ─── WQI SCORE ────────────────────────────────────────────────────────────────
function WQIScore({ value, label, color }: { value: number | null | undefined; label: string; color: string }) {
  const display = value != null ? Math.round(value) : '--';
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontFamily: FONT_LABEL, fontSize: 9, fontWeight: 600, letterSpacing: '0.38em', color: C.textDim, textTransform: 'uppercase', marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontFamily: FONT_DATA, fontSize: 72, lineHeight: 1, color, letterSpacing: '-0.02em', textShadow: `0 0 40px ${color}40` }}>
        {display}
      </div>
      <div style={{ fontFamily: FONT_LABEL, fontSize: 8, letterSpacing: '0.28em', color: `${color}99`, textTransform: 'uppercase', marginTop: 4 }}>
        Weld Quality Index
      </div>
    </div>
  );
}

// ─── ALERT CARD ───────────────────────────────────────────────────────────────
// No corrected/correctedIn — omitted until API supports it.
function AlertCard({ alert, onSeek }: { alert: AlertPayload; onSeek: () => void }) {
  const label     = getRuleLabel(alert.rule_triggered);
  const isCrit    = alert.severity === 'critical';
  return (
    <button
      type="button"
      onClick={onSeek}
      style={{ width: '100%', textAlign: 'left', padding: '8px 0', background: 'none', border: 'none', borderBottom: `1px solid ${C.border}`, cursor: 'pointer' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <span style={{ fontFamily: FONT_LABEL, fontSize: 9, fontWeight: 600, letterSpacing: '0.16em', color: isCrit ? C.novice : C.amber, textTransform: 'uppercase' }}>
          {label}
        </span>
        <span style={{ fontFamily: FONT_DATA, fontSize: 8, color: C.textDim }}>
          T+{(alert.timestamp_ms / 1000).toFixed(1)}s
        </span>
      </div>
      <div style={{ fontFamily: FONT_DATA, fontSize: 7.5, color: C.textDim, marginTop: 2 }}>
        {alert.message}
      </div>
    </button>
  );
}

// ─── SKELETON ─────────────────────────────────────────────────────────────────
// WQI slots exist here so layout does not shift when real WQI fills them.
export function DemoSkeleton() {
  return (
    <div data-testid="demo-skeleton" style={{ background: C.bg, color: C.text, height: '100vh', display: 'grid', gridTemplateRows: '48px 1fr 32px', fontFamily: FONT_LABEL, overflow: 'hidden' }}>
      <header style={{ borderBottom: `1px solid ${C.border}`, background: 'rgba(9,12,16,0.8)', display: 'flex', alignItems: 'center', padding: '0 24px' }}>
        <div style={{ width: 120, height: 12, background: 'rgba(255,255,255,0.05)', borderRadius: 2 }} />
      </header>
      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr 240px' }}>
        {/* Left skeleton */}
        <div style={{ borderRight: `1px solid ${C.border}`, padding: '20px 18px' }}>
          {[1, 2, 3].map(i => <div key={i} style={{ height: 52, background: 'rgba(255,255,255,0.03)', borderRadius: 4, marginBottom: 20 }} />)}
        </div>
        {/* Center skeleton — WQI slots preserve layout */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 28 }}>
          <div style={{ display: 'flex', gap: 64, alignItems: 'flex-end' }}>
            <div data-testid="wqi-skeleton-a" style={{ width: 100, height: 90, background: 'rgba(255,255,255,0.03)', borderRadius: 4 }} />
            <div style={{ width: 40, height: 60, background: 'rgba(255,255,255,0.02)', borderRadius: 4 }} />
            <div data-testid="wqi-skeleton-b" style={{ width: 100, height: 90, background: 'rgba(255,255,255,0.03)', borderRadius: 4 }} />
          </div>
          <div style={{ width: 280, height: 280, borderRadius: '50%', background: 'rgba(255,255,255,0.03)' }} />
          <div style={{ width: 480, height: 4, background: 'rgba(255,255,255,0.03)', borderRadius: 2 }} />
        </div>
        {/* Right skeleton */}
        <div style={{ borderLeft: `1px solid ${C.border}`, padding: '20px 16px' }}>
          {[1, 2, 3, 4].map(i => <div key={i} style={{ height: 40, background: 'rgba(255,255,255,0.03)', borderRadius: 4, marginBottom: 12 }} />)}
        </div>
      </div>
      <footer style={{ borderTop: `1px solid ${C.border}`, background: 'rgba(9,12,16,0.8)' }} />
    </div>
  );
}

// ─── INNER (exported for testing — bypasses use(params)) ─────────────────────
export function DemoPageInner({ sessionIdA, sessionIdB }: { sessionIdA: string; sessionIdB: string }) {
  const [sessionA, setSessionA] = useState<Session | null>(null);
  const [sessionB, setSessionB] = useState<Session | null>(null);
  const [alertsA,  setAlertsA]  = useState<AlertPayload[]>([]);
  const [alertsB,  setAlertsB]  = useState<AlertPayload[]>([]);
  const [alertsErrorA, setAlertsErrorA] = useState<string | null>(null);
  const [alertsErrorB, setAlertsErrorB] = useState<string | null>(null);
  const [loading, setLoading]   = useState(true);
  const [error,   setError]     = useState<string | null>(null);
  const [currentTimestamp, setCurrentTimestamp] = useState<number | null>(null);
  const [isPlaying,    setIsPlaying]    = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);

  // ── Comparison hook (Session objects, not IDs) ──────────────────────────────
  const comparison = useSessionComparison(sessionA, sessionB);

  const firstTimestamp = comparison && comparison.deltas.length > 0
    ? comparison.deltas[0].timestamp_ms : null;
  const lastTimestamp = comparison && comparison.deltas.length > 0
    ? comparison.deltas[comparison.deltas.length - 1].timestamp_ms : null;

  // ── Fetch — exact pattern from compare page ─────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setAlertsErrorA(null);
    setAlertsErrorB(null);
    const load = async () => {
      const [dataA, dataB] = await Promise.all([
        fetchSession(sessionIdA, { limit: 2000, include_thermal: true }),
        fetchSession(sessionIdB, { limit: 2000, include_thermal: true }),
      ]);
      if (cancelled) return;
      setSessionA(dataA);
      setSessionB(dataB);

      // Heat data presence check
      if (!(dataA?.frames ?? []).some(f => f.heat_input_kj_per_mm != null))
        console.warn('sessionA: no heat_input_kj_per_mm; heat chart will be empty');
      if (!(dataB?.frames ?? []).some(f => f.heat_input_kj_per_mm != null))
        console.warn('sessionB: no heat_input_kj_per_mm; heat chart will be empty');

      const [resA, resB] = await Promise.allSettled([
        fetchSessionAlerts(sessionIdA),
        fetchSessionAlerts(sessionIdB),
      ]);
      if (cancelled) return;
      if (resA.status === 'fulfilled') {
        setAlertsA(resA.value.alerts);
      } else {
        logWarn('fetchSessionAlerts', 'A failed', { sessionId: sessionIdA, reason: resA.reason });
        setAlertsErrorA('Alerts unavailable');
      }
      if (resB.status === 'fulfilled') {
        setAlertsB(resB.value.alerts);
      } else {
        logWarn('fetchSessionAlerts', 'B failed', { sessionId: sessionIdB, reason: resB.reason });
        setAlertsErrorB('Alerts unavailable');
      }
    };
    load()
      .catch(err => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          setSessionA(null);
          setSessionB(null);
        }
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [sessionIdA, sessionIdB]);

  // ── Sync currentTimestamp to firstTimestamp on load ─────────────────────────
  useEffect(() => {
    if (firstTimestamp != null && lastTimestamp != null) {
      setCurrentTimestamp(prev => {
        if (prev == null || prev < firstTimestamp || prev > lastTimestamp) return firstTimestamp;
        return prev;
      });
    } else {
      setCurrentTimestamp(null);
    }
  }, [firstTimestamp, lastTimestamp]);

  // ── Playback — exact pattern from compare page ──────────────────────────────
  useEffect(() => {
    if (!isPlaying || lastTimestamp == null || firstTimestamp == null) return;
    const intervalMs = FRAME_INTERVAL_MS / playbackSpeed;
    const id = setInterval(() => {
      setCurrentTimestamp(prev => {
        const base = prev ?? firstTimestamp;
        const next = base + FRAME_INTERVAL_MS;
        if (next >= lastTimestamp) { setIsPlaying(false); return lastTimestamp; }
        return next;
      });
    }, intervalMs);
    return () => clearInterval(id);
  }, [isPlaying, playbackSpeed, firstTimestamp, lastTimestamp]);

  // ── Keyboard (Space = play/pause, arrows = step) ────────────────────────────
  useEffect(() => {
    if (firstTimestamp == null || lastTimestamp == null || lastTimestamp <= firstTimestamp) return;
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLElement && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
      if (e.code === 'Space') { e.preventDefault(); setIsPlaying(p => !p); }
      if (e.code === 'ArrowLeft') {
        e.preventDefault(); setIsPlaying(false);
        setCurrentTimestamp(prev => Math.max(firstTimestamp, (prev ?? firstTimestamp) - FRAME_INTERVAL_MS));
      }
      if (e.code === 'ArrowRight') {
        e.preventDefault(); setIsPlaying(false);
        setCurrentTimestamp(prev => Math.min(lastTimestamp, (prev ?? firstTimestamp) + FRAME_INTERVAL_MS));
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [firstTimestamp, lastTimestamp]);

  // ── Sparkline history from comparison.deltas (time-aligned) — useMemo not useEffect
  // CRITICAL: useMemo avoids 6 setState calls per playback tick (100/sec). useEffect+useState
  // would thrash. Use shared timestamps only — per-session filter misaligns when timestamp sets differ.
  const { aHeatHist, bHeatHist, aAmpHist, bAmpHist, aAngleHist, bAngleHist } = useMemo(() => {
    const empty = { aHeatHist: [] as number[], bHeatHist: [], aAmpHist: [], bAmpHist: [], aAngleHist: [], bAngleHist: [] };
    if (currentTimestamp == null || !comparison) return empty;
    const deltasUpToNow = comparison.deltas.filter(d => d.timestamp_ms <= currentTimestamp).slice(-MAX_HIST);
    const aByTs = new Map((sessionA?.frames ?? []).map(fr => [fr.timestamp_ms, fr]));
    const bByTs = new Map((sessionB?.frames ?? []).map(fr => [fr.timestamp_ms, fr]));
    return {
      aHeatHist: deltasUpToNow.map(d => aByTs.get(d.timestamp_ms)?.heat_input_kj_per_mm).filter((v): v is number => v != null),
      bHeatHist: deltasUpToNow.map(d => bByTs.get(d.timestamp_ms)?.heat_input_kj_per_mm).filter((v): v is number => v != null),
      aAmpHist:  deltasUpToNow.map(d => aByTs.get(d.timestamp_ms)?.amps).filter((v): v is number => v != null),
      bAmpHist:  deltasUpToNow.map(d => bByTs.get(d.timestamp_ms)?.amps).filter((v): v is number => v != null),
      aAngleHist: deltasUpToNow.map(d => aByTs.get(d.timestamp_ms)?.angle_degrees).filter((v): v is number => v != null),
      bAngleHist: deltasUpToNow.map(d => bByTs.get(d.timestamp_ms)?.angle_degrees).filter((v): v is number => v != null),
    };
  }, [currentTimestamp, comparison, sessionA?.frames, sessionB?.frames]);

  // ── Current frame values (for "Current Values" panel only) ─────────────────
  const currentFrameA = currentTimestamp != null && sessionA?.frames
    ? getFrameAtTimestamp(sessionA.frames, currentTimestamp) : null;
  const currentFrameB = currentTimestamp != null && sessionB?.frames
    ? getFrameAtTimestamp(sessionB.frames, currentTimestamp) : null;
  const currentTempA  = currentTimestamp != null && sessionA?.frames
    ? extractCenterTemperatureWithCarryForward(sessionA.frames, currentTimestamp) : null;
  const currentTempB  = currentTimestamp != null && sessionB?.frames
    ? extractCenterTemperatureWithCarryForward(sessionB.frames, currentTimestamp) : null;

  // ── Visible alerts ──────────────────────────────────────────────────────────
  const floorTs = currentTimestamp ?? firstTimestamp ?? 0;
  const visibleAlertsA = useMemo(
    () => alertsA.filter(a => a.timestamp_ms <= floorTs).sort((a, b) => b.timestamp_ms - a.timestamp_ms),
    [alertsA, floorTs]
  );
  const visibleAlertsB = useMemo(
    () => alertsB.filter(a => a.timestamp_ms <= floorTs).sort((a, b) => b.timestamp_ms - a.timestamp_ms),
    [alertsB, floorTs]
  );

  // ── Derived display values ──────────────────────────────────────────────────
  const wqiGap   = sessionA?.score_total != null && sessionB?.score_total != null
    ? Math.abs(Math.round(sessionB.score_total - sessionA.score_total)) : null;
  const noOverlap = !comparison || comparison.deltas.length === 0;
  const duration  = firstTimestamp != null && lastTimestamp != null ? lastTimestamp - firstTimestamp : 0;
  const elapsed   = currentTimestamp != null && firstTimestamp != null ? currentTimestamp - firstTimestamp : 0;
  const pct       = duration > 0 ? ((elapsed / duration) * 100).toFixed(1) : '0';

  // ── Loading / Error ─────────────────────────────────────────────────────────
  if (loading) return <DemoSkeleton />;

  if (error) {
    const is404 = error.toLowerCase().includes('404') || error.toLowerCase().includes('not found');
    return (
      <div style={{ background: C.bg, minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ maxWidth: 480, background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, padding: 24 }}>
          <div style={{ fontFamily: FONT_LABEL, fontSize: 14, fontWeight: 700, color: C.novice, marginBottom: 8 }}>
            {is404 ? 'Demo sessions not found' : 'Failed to load sessions'}
          </div>
          {is404 && (
            <div style={{ fontFamily: FONT_DATA, fontSize: 11, color: C.textDim, marginBottom: 12 }}>
              Run POST /api/dev/seed-mock-sessions to create the expert/novice pair.
            </div>
          )}
          <div style={{ fontFamily: FONT_DATA, fontSize: 11, color: C.textDim, marginBottom: 16 }}>{error}</div>
          <Link href="/dashboard" style={{ fontFamily: FONT_DATA, fontSize: 11, color: C.expert }}>Back to dashboard</Link>
        </div>
      </div>
    );
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div data-testid="demo-loaded" style={{ background: C.bg, color: C.text, height: '100vh', display: 'grid', gridTemplateRows: '48px 1fr 32px', fontFamily: FONT_LABEL, overflow: 'hidden' }}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&display=swap'); * { box-sizing: border-box; margin: 0; padding: 0; }`}</style>

      {/* ── HEADER ── */}
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px', borderBottom: `1px solid ${C.border}`, background: 'rgba(9,12,16,0.8)' }}>
        <div style={{ display: 'flex', alignItems: 'baseline' }}>
          <span style={{ fontFamily: FONT_LABEL, fontSize: 18, fontWeight: 800, letterSpacing: '0.1em', color: C.white }}>WELD</span>
          <span style={{ fontFamily: FONT_LABEL, fontSize: 18, fontWeight: 300, letterSpacing: '0.1em', color: C.expert }}>VIEW</span>
        </div>
        <div style={{ display: 'flex', gap: 32 }}>
          {[['Session A', sessionIdA], ['Session B', sessionIdB]].map(([l, v]) => (
            <div key={l} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 7, fontWeight: 600, letterSpacing: '0.32em', color: C.textDim, textTransform: 'uppercase', marginBottom: 1 }}>{l}</div>
              <div style={{ fontFamily: FONT_DATA, fontSize: 10, color: C.text }}>{v}</div>
            </div>
          ))}
        </div>
        <Link href="/dashboard" style={{ fontFamily: FONT_DATA, fontSize: 9, color: C.textDim, letterSpacing: '0.1em' }}>← Dashboard</Link>
      </header>

      {/* ── MAIN GRID ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr 240px', overflow: 'hidden' }}>

        {/* LEFT — Sparklines + Current Values */}
        <div style={{ borderRight: `1px solid ${C.border}`, background: 'rgba(13,17,23,0.9)', padding: '20px 18px', overflowY: 'auto' }}>
          <div style={{ fontSize: 8, fontWeight: 600, letterSpacing: '0.32em', color: C.textDim, textTransform: 'uppercase', marginBottom: 18 }}>
            Parameter Comparison
          </div>
          <Sparkline noviceHistory={aHeatHist}  expertHistory={bHeatHist}  specMin={0.55} specMax={0.80} dataMin={0.50} dataMax={1.25} label="Heat Input" unit="kJ/mm" />
          <Sparkline noviceHistory={aAmpHist}   expertHistory={bAmpHist}   specMin={150}  specMax={190}  dataMin={130}  dataMax={240}  label="Amperage"   unit="A"     />
          <Sparkline noviceHistory={aAngleHist} expertHistory={bAngleHist} specMin={60}   specMax={75}   dataMin={55}   dataMax={95}   label="Torch Angle" unit="°"    />

          {/* Current Values — single frame via getFrameAtTimestamp */}
          <div style={{ marginTop: 4, paddingTop: 16, borderTop: `1px solid ${C.border}` }}>
            <div style={{ fontSize: 8, fontWeight: 600, letterSpacing: '0.28em', color: C.textDim, textTransform: 'uppercase', marginBottom: 12 }}>Current Values</div>
            {([
              ['Heat',  currentFrameA?.heat_input_kj_per_mm?.toFixed(2) ?? '--', currentFrameB?.heat_input_kj_per_mm?.toFixed(2) ?? '--', 'kJ/mm'],
              ['Amp',   currentFrameA?.amps != null ? String(Math.round(currentFrameA.amps)) : '--', currentFrameB?.amps != null ? String(Math.round(currentFrameB.amps)) : '--', 'A'],
              ['Angle', currentFrameA?.angle_degrees != null ? String(Math.round(currentFrameA.angle_degrees)) : '--', currentFrameB?.angle_degrees != null ? String(Math.round(currentFrameB.angle_degrees)) : '--', '°'],
              ['Temp',  currentTempA != null ? String(Math.round(currentTempA)) : '--', currentTempB != null ? String(Math.round(currentTempB)) : '--', '°C'],
            ] as [string, string, string, string][]).map(([l, av, bv, u]) => (
              <div key={l} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: 8, letterSpacing: '0.2em', color: C.textDim, textTransform: 'uppercase', width: 40 }}>{l}</span>
                <span style={{ fontFamily: FONT_DATA, fontSize: 11, color: C.novice }}>{av}<span style={{ fontSize: 8, color: 'rgba(255,69,69,0.4)', marginLeft: 2 }}>{u}</span></span>
                <span style={{ fontSize: 7, color: C.textDim }}>vs</span>
                <span style={{ fontFamily: FONT_DATA, fontSize: 11, color: C.expert }}>{bv}<span style={{ fontSize: 8, color: 'rgba(0,229,160,0.4)', marginLeft: 2 }}>{u}</span></span>
              </div>
            ))}
          </div>
        </div>

        {/* CENTER — WQI + BeadDiff + Timeline */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '20px 24px', gap: 0, position: 'relative' }}>
          {noOverlap && (
            <div style={{ background: 'rgba(255,176,32,0.08)', border: `1px solid rgba(255,176,32,0.2)`, borderRadius: 6, padding: '10px 16px', marginBottom: 16, fontSize: 10, color: C.amber, letterSpacing: '0.1em' }}>
              No overlapping frames. Sessions must share timestamps.
            </div>
          )}

          {/* WQI scores — same layout as investor demo */}
          <div style={{ display: 'flex', gap: 64, marginBottom: 28, alignItems: 'flex-end' }}>
            <WQIScore value={sessionA?.score_total} label="Session A" color={C.novice} />
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', paddingBottom: 16, gap: 6 }}>
              <div style={{ fontSize: 7, fontWeight: 600, letterSpacing: '0.3em', color: C.textDim, textTransform: 'uppercase' }}>Gap</div>
              <div style={{ fontFamily: FONT_DATA, fontSize: 22, color: 'rgba(255,255,255,0.2)', letterSpacing: '-0.01em' }}>
                {wqiGap ?? '--'}
              </div>
              <div style={{ fontSize: 7, color: C.textDim, letterSpacing: '0.18em' }}>pts</div>
            </div>
            <WQIScore value={sessionB?.score_total} label="Session B" color={C.expert} />
          </div>

          {/* BeadDiff — static placeholder, same circular container as investor demo */}
          <div style={{ position: 'relative' }}>
            <div style={{ position: 'absolute', inset: -14, borderRadius: '50%', border: '1px solid rgba(255,255,255,0.05)', pointerEvents: 'none' }} />
            <div style={{ position: 'absolute', inset: -6, borderRadius: '50%', border: '1px solid rgba(255,255,255,0.03)', pointerEvents: 'none' }} />
            <div style={{ width: 'min(calc(100vh - 260px), 420px)', aspectRatio: '1/1', borderRadius: '50%', overflow: 'hidden', border: '1px solid rgba(255,255,255,0.08)', boxShadow: '0 0 80px rgba(0,0,0,0.9), inset 0 0 40px rgba(0,0,0,0.5)' }}>
              <BeadDiffPlaceholder />
            </div>
          </div>

          {/* Timeline + Scrub */}
          {firstTimestamp != null && lastTimestamp != null && lastTimestamp > firstTimestamp && (
            <div style={{ width: '100%', maxWidth: 480, marginTop: 44 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <button
                    type="button"
                    onClick={() => setIsPlaying(p => !p)}
                    disabled={noOverlap}
                    aria-label={isPlaying ? 'Pause playback' : 'Play playback'}
                    style={{ fontFamily: FONT_LABEL, fontSize: 8, fontWeight: 600, letterSpacing: '0.22em', textTransform: 'uppercase', padding: '4px 10px', background: 'rgba(255,255,255,0.06)', border: `1px solid ${C.borderBright}`, color: C.white, cursor: 'pointer', borderRadius: 2, opacity: noOverlap ? 0.4 : 1 }}
                  >
                    {isPlaying ? 'Pause' : 'Play'}
                  </button>
                  {/* Playback speed */}
                  {[1, 2, 4].map(s => (
                    <button key={s} type="button" onClick={() => setPlaybackSpeed(s)} style={{ fontFamily: FONT_DATA, fontSize: 8, padding: '3px 7px', background: playbackSpeed === s ? 'rgba(255,255,255,0.1)' : 'none', border: `1px solid ${playbackSpeed === s ? C.borderBright : C.border}`, color: playbackSpeed === s ? C.white : C.textDim, cursor: 'pointer', borderRadius: 2 }}>
                      {s}×
                    </button>
                  ))}
                </div>
                <span style={{ fontFamily: FONT_DATA, fontSize: 9, color: C.textDim }}>
                  {(elapsed / 1000).toFixed(2)}s / {(duration / 1000).toFixed(2)}s
                </span>
              </div>
              {/* Progress bar with alert markers */}
              <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', position: 'relative', marginBottom: 4 }}>
                {[...alertsA, ...alertsB].map((a, i) => (
                  <div key={i} style={{ position: 'absolute', left: `${((a.timestamp_ms - firstTimestamp) / duration) * 100}%`, top: -2, width: 1, height: 5, background: (currentTimestamp ?? 0) >= a.timestamp_ms ? C.novice : 'rgba(255,69,69,0.2)' }} />
                ))}
                <div style={{ height: '100%', width: `${pct}%`, background: 'linear-gradient(90deg, rgba(255,255,255,0.15), rgba(255,255,255,0.35))', position: 'relative', transition: 'width 0.08s linear' }}>
                  <div style={{ position: 'absolute', right: -4, top: '50%', transform: 'translateY(-50%)', width: 8, height: 8, borderRadius: '50%', background: C.white, boxShadow: '0 0 8px rgba(255,255,255,0.6)' }} />
                </div>
              </div>
              <input
                type="range"
                min={firstTimestamp}
                max={lastTimestamp}
                step={FRAME_INTERVAL_MS}
                value={currentTimestamp ?? firstTimestamp}
                disabled={noOverlap}
                onChange={e => {
                  setIsPlaying(false);
                  const val = Number(e.target.value);
                  setCurrentTimestamp(Number.isFinite(val) ? Math.max(firstTimestamp, Math.min(lastTimestamp, val)) : firstTimestamp);
                }}
                style={{ width: '100%', accentColor: C.expert }}
              />
            </div>
          )}
        </div>

        {/* RIGHT — Alert Feed (two columns: A | B) */}
        <div style={{ borderLeft: `1px solid ${C.border}`, background: 'rgba(13,17,23,0.9)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ padding: '16px 16px 12px', borderBottom: `1px solid ${C.border}` }}>
            <div style={{ fontSize: 8, fontWeight: 600, letterSpacing: '0.32em', color: C.textDim, textTransform: 'uppercase', marginBottom: 6 }}>Alert Feed</div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontFamily: FONT_DATA, fontSize: 9, color: alertsErrorA ? C.amber : C.novice }}>
                A: {alertsErrorA ? '—' : visibleAlertsA.length}
              </span>
              <span style={{ fontFamily: FONT_DATA, fontSize: 9, color: alertsErrorB ? C.amber : C.expert }}>
                B: {alertsErrorB ? '—' : visibleAlertsB.length}
              </span>
            </div>
          </div>
          {/* Two-column alert layout */}
          <div style={{ flex: 1, overflow: 'hidden', display: 'grid', gridTemplateColumns: '1fr 1fr' }}>
            {/* Column A */}
            <div style={{ borderRight: `1px solid ${C.border}`, padding: '10px 10px', overflowY: 'auto' }}>
              <div style={{ fontSize: 7, fontWeight: 600, letterSpacing: '0.28em', color: C.textDim, textTransform: 'uppercase', marginBottom: 8 }}>Session A</div>
              {alertsErrorA
                ? <div style={{ fontFamily: FONT_DATA, fontSize: 9, color: C.amber }}>Alerts unavailable</div>
                : visibleAlertsA.length === 0
                  ? <div style={{ fontFamily: FONT_DATA, fontSize: 9, color: C.textDim }}>No alerts yet</div>
                  : visibleAlertsA.map(alert => (
                      <AlertCard
                        key={`a-${alert.frame_index}-${alert.timestamp_ms}-${alert.rule_triggered}`}
                        alert={alert}
                        onSeek={() => { setCurrentTimestamp(alert.timestamp_ms); setIsPlaying(false); }}
                      />
                    ))
              }
            </div>
            {/* Column B */}
            <div style={{ padding: '10px 10px', overflowY: 'auto' }}>
              <div style={{ fontSize: 7, fontWeight: 600, letterSpacing: '0.28em', color: C.textDim, textTransform: 'uppercase', marginBottom: 8 }}>Session B</div>
              {alertsErrorB
                ? <div style={{ fontFamily: FONT_DATA, fontSize: 9, color: C.amber }}>Alerts unavailable</div>
                : visibleAlertsB.length === 0
                  ? <div style={{ fontFamily: FONT_DATA, fontSize: 9, color: C.textDim }}>No alerts yet</div>
                  : visibleAlertsB.map(alert => (
                      <AlertCard
                        key={`b-${alert.frame_index}-${alert.timestamp_ms}-${alert.rule_triggered}`}
                        alert={alert}
                        onSeek={() => { setCurrentTimestamp(alert.timestamp_ms); setIsPlaying(false); }}
                      />
                    ))
              }
            </div>
          </div>
        </div>
      </div>

      {/* ── FOOTER ── */}
      <footer style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px', borderTop: `1px solid ${C.border}`, background: 'rgba(9,12,16,0.8)' }}>
        <span style={{ fontSize: 7.5, fontWeight: 400, letterSpacing: '0.22em', color: C.textDim, textTransform: 'uppercase' }}>WELDVIEW SYS v1.0</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <div style={{ width: 5, height: 5, borderRadius: '50%', background: '#00e87a', boxShadow: '0 0 6px #00e87a' }} />
          <span style={{ fontSize: 7.5, fontWeight: 600, letterSpacing: '0.28em', color: '#00e87a', textTransform: 'uppercase' }}>
            {isPlaying ? 'Replay Active' : 'Ready'}
          </span>
        </div>
        <span style={{ fontSize: 7.5, fontWeight: 400, letterSpacing: '0.22em', color: C.textDim, textTransform: 'uppercase' }}>
          {sessionIdA} vs {sessionIdB}
        </span>
      </footer>
    </div>
  );
}

// ─── ROUTE WRAPPER ────────────────────────────────────────────────────────────
export default function DemoPage({
  params,
}: {
  params: Promise<{ sessionIdA: string; sessionIdB: string }>;
}) {
  return (
    <Suspense fallback={<DemoSkeleton />}>
      <DemoPageWithAsyncParams params={params} />
    </Suspense>
  );
}

function DemoPageWithAsyncParams({
  params,
}: {
  params: Promise<{ sessionIdA: string; sessionIdB: string }>;
}) {
  const { sessionIdA, sessionIdB } = use(params);
  return <DemoPageInner sessionIdA={sessionIdA} sessionIdB={sessionIdB} />;
}
Create my-app/src/__tests__/app/demo/page.test.tsx:
tsximport { describe } from '@jest/globals';

describe('DemoPage', () => {
  // Tests added in Step 3
});
Verification:
bash# File exists
ls my-app/src/app/demo/\[sessionIdA\]/\[sessionIdB\]/page.tsx

# TypeScript compiles (no emit)
cd my-app && npx tsc --noEmit 2>&1 | grep -i "demo" | head -20
# Expect: no errors referencing demo/page.tsx

# Test runner finds and passes the empty suite
cd my-app && npm test -- src/__tests__/app/demo/page.test.tsx 2>&1 | tail -5

# No mock data in the file
grep -n "KF_NOVICE\|KF_EXPERT\|interp(" my-app/src/app/demo/\[sessionIdA\]/\[sessionIdB\]/page.tsx
# Must return 0 matches

# Landing page redirects
curl -sI http://localhost:3000/demo 2>/dev/null | grep -i location
# Expect: Location: /demo/sess_novice_aluminium_001_001/sess_expert_aluminium_001_001 (or 307/308 redirect)
Git: git add my-app/src/app/demo/page.tsx my-app/src/app/demo/\[sessionIdA\]/\[sessionIdB\]/page.tsx my-app/src/__tests__/app/demo/page.test.tsx && git commit -m "step 2: create demo page wired to real API"

Step 3 — Add Tests
File: my-app/src/__tests__/app/demo/page.test.tsx
If the import `from '@/app/demo/[sessionIdA]/[sessionIdB]/page'` fails to resolve, check tsconfig.json paths and Jest moduleNameMapper for bracket-directory handling. The compare page test uses a colocated pattern: test at `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.test.tsx` with `import { ComparePageInner } from './page'`. If bracket paths fail, move the demo test to `my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.test.tsx` and use `import { DemoPageInner } from './page'`.

Before writing tests, reconcile baseSession against Session type:
bashgrep -n "^  [a-z_]" my-app/src/types/session.ts | head -35
# Every non-optional field (no ?) must exist in baseSession. Add any missing required fields.
Replace empty describe with:
tsximport React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DemoPageInner } from '@/app/demo/[sessionIdA]/[sessionIdB]/page';
import * as api from '@/lib/api';

jest.mock('@/lib/api');

const mockUseSessionComparison = jest.fn();
jest.mock('@/hooks/useSessionComparison', () => ({
  useSessionComparison: (...args: unknown[]) => mockUseSessionComparison(...args),
}));

// Reconcile with Session type: grep "^  [a-z_]" my-app/src/types/session.ts — every non-optional field must be present.
const baseSession = {
  session_id: 'sess_a',
  operator_id: 'op_1',
  start_time: '2026-01-01T00:00:00Z',
  weld_type: 'butt_joint',
  thermal_sample_interval_ms: 100,
  thermal_directions: ['center'],
  thermal_distance_interval_mm: 10,
  sensor_sample_rate_hz: 100,
  status: 'complete' as const,
  frame_count: 2,
  expected_frame_count: 2,
  last_successful_frame_index: 1,
  validation_errors: [] as string[],
  completed_at: '2026-01-01T00:00:15Z',
  score_total: 72,
  frames: [
    { timestamp_ms: 0, amps: 180, volts: 22, angle_degrees: 68, heat_input_kj_per_mm: 0.65, thermal_snapshots: [], has_thermal_data: false },
    { timestamp_ms: 1000, amps: 182, volts: 22, angle_degrees: 69, heat_input_kj_per_mm: 0.67, thermal_snapshots: [], has_thermal_data: false },
  ],
};

beforeEach(() => {
  mockUseSessionComparison.mockReturnValue({
    deltas: [{ timestamp_ms: 0 }, { timestamp_ms: 1000 }],
    shared_count: 2,
    total_a: 2,
    total_b: 2,
  });
  (api.fetchSession as jest.Mock).mockImplementation((id: string) =>
    Promise.resolve({ ...baseSession, session_id: id })
  );
  (api.fetchSessionAlerts as jest.Mock).mockResolvedValue({ alerts: [] });
});

afterEach(() => jest.clearAllMocks());

test('renders loaded state after fetch resolves', async () => {
  render(<DemoPageInner sessionIdA="sess_a" sessionIdB="sess_b" />);
  // Skeleton visible during load
  expect(screen.getByTestId('demo-skeleton')).toBeInTheDocument();
  await waitFor(() => expect(screen.getByTestId('demo-loaded')).toBeInTheDocument());
  expect(screen.queryByTestId('demo-skeleton')).not.toBeInTheDocument();
});

test('WQI shows score_total when present', async () => {
  render(<DemoPageInner sessionIdA="sess_a" sessionIdB="sess_b" />);
  await waitFor(() => screen.getByTestId('demo-loaded'));
  // score_total: 72 → both sessions use same mock, both show 72
  expect(screen.getAllByText('72').length).toBeGreaterThanOrEqual(1);
});

test('WQI shows "--" when score_total is null', async () => {
  (api.fetchSession as jest.Mock).mockImplementation((id: string) =>
    Promise.resolve({ ...baseSession, session_id: id, score_total: null })
  );
  render(<DemoPageInner sessionIdA="sess_a" sessionIdB="sess_b" />);
  await waitFor(() => screen.getByTestId('demo-loaded'));
  expect(screen.getAllByText('--').length).toBeGreaterThanOrEqual(1);
});

test('shows "Alerts unavailable" when fetchSessionAlerts rejects for session A', async () => {
  (api.fetchSessionAlerts as jest.Mock).mockImplementation((id: string) =>
    id === 'sess_a' ? Promise.reject(new Error('network')) : Promise.resolve({ alerts: [] })
  );
  render(<DemoPageInner sessionIdA="sess_a" sessionIdB="sess_b" />);
  await waitFor(() => screen.getByTestId('demo-loaded'));
  expect(screen.getByText(/Alerts unavailable/i)).toBeInTheDocument();
});

test('shows error page on 404', async () => {
  (api.fetchSession as jest.Mock).mockRejectedValue(new Error('404 not found'));
  render(<DemoPageInner sessionIdA="sess_a" sessionIdB="sess_b" />);
  await waitFor(() => screen.getByText(/Demo sessions not found/i));
});

test('no overlapping frames shows message', async () => {
  mockUseSessionComparison.mockReturnValueOnce({
    deltas: [],
    shared_count: 0,
    total_a: 2,
    total_b: 2,
  });
  render(<DemoPageInner sessionIdA="sess_a" sessionIdB="sess_b" />);
  await waitFor(() => screen.getByTestId('demo-loaded'));
  expect(screen.getByText(/No overlapping frames/i)).toBeInTheDocument();
});
Verification:
bashcd my-app && npx tsc --noEmit 2>&1
# Exit 0 required. If baseSession causes Session/Frame type errors, add missing required fields from session.ts.

cd my-app && npm test -- src/__tests__/app/demo/page.test.tsx 2>&1
# All tests pass. 0 failures.

# Confirm no interp/keyframe logic crept in
grep -n "KF_NOVICE\|KF_EXPERT\|interp(\|requestAnimationFrame" my-app/src/app/demo/\[sessionIdA\]/\[sessionIdB\]/page.tsx
# Must return 0 matches
Git: git add my-app/src/__tests__/app/demo/page.test.tsx && git commit -m "step 3: add demo page tests"

Regression Guard
bashcd my-app && npm test -- src/app/compare 2>&1 | tail -5
# All pass — compare page untouched

cd my-app && npm test -- src/__tests__/utils/frameUtils 2>&1 | tail -5
# All pass

cd my-app && npm test -- --testPathIgnorePatterns=e2e 2>&1 | grep -E "Tests:|passed"
# Count >= pre-flight baseline

npx tsc --noEmit 2>&1 | grep -v "node_modules" | head -20
# 0 errors

Rollback
bashgit revert HEAD~3..HEAD
cd my-app && npm test

Success Criteria
| Feature | Verification |
|---------|--------------|
| API linking | fetchSession hits GET /api/sessions/{id}; fetchSessionAlerts hits GET /api/sessions/{id}/alerts. Backend main.py includes sessions_router at prefix /api. |
| Landing page | /demo redirects to /demo/sess_novice_aluminium_001_001/sess_expert_aluminium_001_001 |
| Route works | curl http://localhost:3000/demo/sess_a/sess_b → 200 |
| No mock data | grep -n "KF_NOVICE|interp(" page.tsx → 0 matches |
| Skeleton WQI slots | getByTestId('wqi-skeleton-a') during load |
| No layout shift | demo-skeleton → demo-loaded same grid structure |
| WQI null → "--" | Test passes |
| Alerts unavailable | Test passes |
| No overlap | Test passes (mockReturnValueOnce) |
| History time-aligned | grep "comparison.deltas" page.tsx → used in useMemo. NOT per-session independent filter. |
| No history thrashing | grep "useMemo" page.tsx → history arrays from useMemo, not useEffect+useState. Avoids 6 setState/100ms during playback. |
| Playback FRAME_INTERVAL_MS | grep "FRAME_INTERVAL_MS" page.tsx → 2+ matches |
| Test baseSession shape | session_id not id; has frames, score_total, required Session fields |
| TypeScript clean | tsc --noEmit → 0 errors |