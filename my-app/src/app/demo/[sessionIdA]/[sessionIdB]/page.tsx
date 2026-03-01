'use client';

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
  bg: '#090c10',
  surface: '#0d1117',
  border: 'rgba(255,255,255,0.07)',
  borderBright: 'rgba(255,255,255,0.14)',
  text: '#dce8f0',
  textDim: 'rgba(180,200,215,0.38)',
  novice: '#ff4545',
  expert: '#00e5a0',
  specBand: 'rgba(255,255,255,0.04)',
  white: '#f0f6ff',
  amber: '#ffb020',
};
const FONT_LABEL = "'Syne', sans-serif";
const FONT_DATA = "'DM Mono', monospace";
const MAX_HIST = 60;

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
  const W = 100,
    H = 52;
  const range = dataMax - dataMin;
  const toY = (v: number) =>
    range <= 0 ? H / 2 : H - ((v - dataMin) / range) * H;
  const toX = (i: number, len: number) => (len > 1 ? (i / (len - 1)) * W : 0);
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
        <span
          style={{
            fontFamily: FONT_LABEL,
            fontSize: 9,
            letterSpacing: '0.28em',
            color: C.textDim,
            textTransform: 'uppercase',
          }}
        >
          {label}
        </span>
        <span style={{ fontFamily: FONT_DATA, fontSize: 9, color: C.textDim }}>{unit}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} style={{ display: 'block', overflow: 'visible' }}>
        <rect
          x={0}
          y={Math.min(specY1, specY2)}
          width={W}
          height={Math.abs(specY2 - specY1)}
          fill={C.specBand}
        />
        <line
          x1={0}
          y1={specY1}
          x2={W}
          y2={specY1}
          stroke="rgba(255,255,255,0.1)"
          strokeWidth={0.5}
          strokeDasharray="2,2"
        />
        {expertHistory.length > 1 && (
          <path d={pathOf(expertHistory)} fill="none" stroke={C.expert} strokeWidth={1} opacity={0.7} />
        )}
        {noviceHistory.length > 1 && (
          <path d={pathOf(noviceHistory)} fill="none" stroke={C.novice} strokeWidth={1} opacity={0.85} />
        )}
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
    const W = (canvas.width = canvas.offsetWidth * dpr);
    const H = (canvas.height = canvas.offsetHeight * dpr);
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const cx = W / 2,
      cy = H / 2;
    const R = Math.min(W, H) / 2 - 2;
    ctx.clearRect(0, 0, W, H);
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, R, 0, Math.PI * 2);
    ctx.clip();
    ctx.fillStyle = '#07090d';
    ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = 'rgba(255,255,255,0.03)';
    ctx.lineWidth = 0.8;
    for (let x = 0; x < W; x += W / 10) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, H);
      ctx.stroke();
    }
    for (let y = 0; y < H; y += H / 10) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(W, y);
      ctx.stroke();
    }
    ctx.fillStyle = 'rgba(180,200,215,0.2)';
    ctx.font = `${R * 0.055}px DM Mono`;
    ctx.textAlign = 'center';
    ctx.fillText('BEAD PROFILE — DERIVED', cx, cy - 8);
    ctx.fillText('(not sensor-measured)', cx, cy + 10);
    ctx.restore();
    ctx.strokeStyle = 'rgba(255,255,255,0.09)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(cx, cy, R - 0.5, 0, Math.PI * 2);
    ctx.stroke();
  }, []);
  return (
    <canvas
      ref={ref}
      style={{ width: '100%', height: '100%', display: 'block', borderRadius: '50%' }}
    />
  );
}

// ─── WQI SCORE ────────────────────────────────────────────────────────────────
function WQIScore({
  value,
  label,
  color,
}: {
  value: number | null | undefined;
  label: string;
  color: string;
}) {
  const display = value != null ? Math.round(value) : '--';
  return (
    <div style={{ textAlign: 'center' }}>
      <div
        style={{
          fontFamily: FONT_LABEL,
          fontSize: 9,
          fontWeight: 600,
          letterSpacing: '0.38em',
          color: C.textDim,
          textTransform: 'uppercase',
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: FONT_DATA,
          fontSize: 72,
          lineHeight: 1,
          color,
          letterSpacing: '-0.02em',
          textShadow: `0 0 40px ${color}40`,
        }}
      >
        {display}
      </div>
      <div
        style={{
          fontFamily: FONT_LABEL,
          fontSize: 8,
          letterSpacing: '0.28em',
          color: `${color}99`,
          textTransform: 'uppercase',
          marginTop: 4,
        }}
      >
        Weld Quality Index
      </div>
    </div>
  );
}

// ─── ALERT CARD ───────────────────────────────────────────────────────────────
// No corrected/correctedIn — omitted until API supports it.
function AlertCard({ alert, onSeek }: { alert: AlertPayload; onSeek: () => void }) {
  const label = getRuleLabel(alert.rule_triggered);
  const isCrit = alert.severity === 'critical';
  return (
    <button
      type="button"
      onClick={onSeek}
      style={{
        width: '100%',
        textAlign: 'left',
        padding: '8px 0',
        background: 'none',
        border: 'none',
        borderBottom: `1px solid ${C.border}`,
        cursor: 'pointer',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <span
          style={{
            fontFamily: FONT_LABEL,
            fontSize: 9,
            fontWeight: 600,
            letterSpacing: '0.16em',
            color: isCrit ? C.novice : C.amber,
            textTransform: 'uppercase',
          }}
        >
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
    <div
      data-testid="demo-skeleton"
      style={{
        background: C.bg,
        color: C.text,
        height: '100vh',
        display: 'grid',
        gridTemplateRows: '48px 1fr 32px',
        fontFamily: FONT_LABEL,
        overflow: 'hidden',
      }}
    >
      <header
        style={{
          borderBottom: `1px solid ${C.border}`,
          background: 'rgba(9,12,16,0.8)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 24px',
        }}
      >
        <div style={{ width: 120, height: 12, background: 'rgba(255,255,255,0.05)', borderRadius: 2 }} />
      </header>
      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr 240px' }}>
        <div style={{ borderRight: `1px solid ${C.border}`, padding: '20px 18px' }}>
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              style={{
                height: 52,
                background: 'rgba(255,255,255,0.03)',
                borderRadius: 4,
                marginBottom: 20,
              }}
            />
          ))}
        </div>
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 28,
          }}
        >
          <div style={{ display: 'flex', gap: 64, alignItems: 'flex-end' }}>
            <div
              data-testid="wqi-skeleton-a"
              style={{
                width: 100,
                height: 90,
                background: 'rgba(255,255,255,0.03)',
                borderRadius: 4,
              }}
            />
            <div
              style={{
                width: 40,
                height: 60,
                background: 'rgba(255,255,255,0.02)',
                borderRadius: 4,
              }}
            />
            <div
              data-testid="wqi-skeleton-b"
              style={{
                width: 100,
                height: 90,
                background: 'rgba(255,255,255,0.03)',
                borderRadius: 4,
              }}
            />
          </div>
          <div
            style={{
              width: 280,
              height: 280,
              borderRadius: '50%',
              background: 'rgba(255,255,255,0.03)',
            }}
          />
          <div
            style={{
              width: 480,
              height: 4,
              background: 'rgba(255,255,255,0.03)',
              borderRadius: 2,
            }}
          />
        </div>
        <div style={{ borderLeft: `1px solid ${C.border}`, padding: '20px 16px' }}>
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              style={{
                height: 40,
                background: 'rgba(255,255,255,0.03)',
                borderRadius: 4,
                marginBottom: 12,
              }}
            />
          ))}
        </div>
      </div>
      <footer
        style={{
          borderTop: `1px solid ${C.border}`,
          background: 'rgba(9,12,16,0.8)',
        }}
      />
    </div>
  );
}

// ─── INNER (exported for testing — bypasses use(params)) ─────────────────────
export function DemoPageInner({
  sessionIdA,
  sessionIdB,
}: {
  sessionIdA: string;
  sessionIdB: string;
}) {
  const [sessionA, setSessionA] = useState<Session | null>(null);
  const [sessionB, setSessionB] = useState<Session | null>(null);
  const [alertsA, setAlertsA] = useState<AlertPayload[]>([]);
  const [alertsB, setAlertsB] = useState<AlertPayload[]>([]);
  const [alertsErrorA, setAlertsErrorA] = useState<string | null>(null);
  const [alertsErrorB, setAlertsErrorB] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentTimestamp, setCurrentTimestamp] = useState<number | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);

  const comparison = useSessionComparison(sessionA, sessionB);

  const firstTimestamp =
    comparison && comparison.deltas.length > 0 ? comparison.deltas[0].timestamp_ms : null;
  const lastTimestamp =
    comparison && comparison.deltas.length > 0
      ? comparison.deltas[comparison.deltas.length - 1].timestamp_ms
      : null;

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

      if (!(dataA?.frames ?? []).some((f) => f.heat_input_kj_per_mm != null))
        logWarn('DemoPage', 'sessionA: no heat_input_kj_per_mm; heat chart will be empty', {
          sessionId: sessionIdA,
        });
      if (!(dataB?.frames ?? []).some((f) => f.heat_input_kj_per_mm != null))
        logWarn('DemoPage', 'sessionB: no heat_input_kj_per_mm; heat chart will be empty', {
          sessionId: sessionIdB,
        });

      const [resA, resB] = await Promise.allSettled([
        fetchSessionAlerts(sessionIdA),
        fetchSessionAlerts(sessionIdB),
      ]);
      if (cancelled) return;
      if (resA.status === 'fulfilled') {
        setAlertsA(resA.value.alerts);
        setAlertsErrorA(null);
      } else {
        logWarn('fetchSessionAlerts', 'A failed', { sessionId: sessionIdA, reason: resA.reason });
        setAlertsErrorA('Alerts unavailable');
        setAlertsA([]);
      }
      if (resB.status === 'fulfilled') {
        setAlertsB(resB.value.alerts);
        setAlertsErrorB(null);
      } else {
        logWarn('fetchSessionAlerts', 'B failed', { sessionId: sessionIdB, reason: resB.reason });
        setAlertsErrorB('Alerts unavailable');
        setAlertsB([]);
      }
    };
    load()
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          setSessionA(null);
          setSessionB(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionIdA, sessionIdB]);

  useEffect(() => {
    if (firstTimestamp != null && lastTimestamp != null) {
      setCurrentTimestamp((prev) => {
        if (prev == null || prev < firstTimestamp || prev > lastTimestamp) return firstTimestamp;
        return prev;
      });
    } else {
      setCurrentTimestamp(null);
    }
  }, [firstTimestamp, lastTimestamp]);

  useEffect(() => {
    if (!isPlaying || lastTimestamp == null || firstTimestamp == null) return;
    const intervalMs = FRAME_INTERVAL_MS / playbackSpeed;
    const id = setInterval(() => {
      setCurrentTimestamp((prev) => {
        const base = prev ?? firstTimestamp;
        const next = base + FRAME_INTERVAL_MS;
        if (next >= lastTimestamp) {
          setIsPlaying(false);
          return lastTimestamp;
        }
        return next;
      });
    }, intervalMs);
    return () => clearInterval(id);
  }, [isPlaying, playbackSpeed, firstTimestamp, lastTimestamp]);

  useEffect(() => {
    if (firstTimestamp == null || lastTimestamp == null || lastTimestamp <= firstTimestamp) return;
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLElement && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName))
        return;
      if (e.code === 'Space') {
        e.preventDefault();
        setIsPlaying((p) => !p);
      }
      if (e.code === 'ArrowLeft') {
        e.preventDefault();
        setIsPlaying(false);
        setCurrentTimestamp((prev) =>
          Math.max(firstTimestamp, (prev ?? firstTimestamp) - FRAME_INTERVAL_MS)
        );
      }
      if (e.code === 'ArrowRight') {
        e.preventDefault();
        setIsPlaying(false);
        setCurrentTimestamp((prev) =>
          Math.min(lastTimestamp, (prev ?? firstTimestamp) + FRAME_INTERVAL_MS)
        );
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [firstTimestamp, lastTimestamp]);

  const { aHeatHist, bHeatHist, aAmpHist, bAmpHist, aAngleHist, bAngleHist } = useMemo(() => {
    const empty = {
      aHeatHist: [] as number[],
      bHeatHist: [] as number[],
      aAmpHist: [] as number[],
      bAmpHist: [] as number[],
      aAngleHist: [] as number[],
      bAngleHist: [] as number[],
    };
    if (currentTimestamp == null || !comparison) return empty;
    const deltasUpToNow = comparison.deltas
      .filter((d) => d.timestamp_ms <= currentTimestamp)
      .slice(-MAX_HIST);
    const aByTs = new Map((sessionA?.frames ?? []).map((fr) => [fr.timestamp_ms, fr]));
    const bByTs = new Map((sessionB?.frames ?? []).map((fr) => [fr.timestamp_ms, fr]));
    return {
      aHeatHist: deltasUpToNow
        .map((d) => aByTs.get(d.timestamp_ms)?.heat_input_kj_per_mm)
        .filter((v): v is number => v != null),
      bHeatHist: deltasUpToNow
        .map((d) => bByTs.get(d.timestamp_ms)?.heat_input_kj_per_mm)
        .filter((v): v is number => v != null),
      aAmpHist: deltasUpToNow
        .map((d) => aByTs.get(d.timestamp_ms)?.amps)
        .filter((v): v is number => v != null),
      bAmpHist: deltasUpToNow
        .map((d) => bByTs.get(d.timestamp_ms)?.amps)
        .filter((v): v is number => v != null),
      aAngleHist: deltasUpToNow
        .map((d) => aByTs.get(d.timestamp_ms)?.angle_degrees)
        .filter((v): v is number => v != null),
      bAngleHist: deltasUpToNow
        .map((d) => bByTs.get(d.timestamp_ms)?.angle_degrees)
        .filter((v): v is number => v != null),
    };
  }, [currentTimestamp, comparison, sessionA?.frames, sessionB?.frames]);

  const currentFrameA =
    currentTimestamp != null && sessionA?.frames
      ? getFrameAtTimestamp(sessionA.frames, currentTimestamp)
      : null;
  const currentFrameB =
    currentTimestamp != null && sessionB?.frames
      ? getFrameAtTimestamp(sessionB.frames, currentTimestamp)
      : null;
  const currentTempA =
    currentTimestamp != null && sessionA?.frames
      ? extractCenterTemperatureWithCarryForward(sessionA.frames, currentTimestamp)
      : null;
  const currentTempB =
    currentTimestamp != null && sessionB?.frames
      ? extractCenterTemperatureWithCarryForward(sessionB.frames, currentTimestamp)
      : null;

  const floorTs = currentTimestamp ?? firstTimestamp ?? 0;
  const visibleAlertsA = useMemo(
    () =>
      alertsA
        .filter((a) => a.timestamp_ms <= floorTs)
        .sort((a, b) => b.timestamp_ms - a.timestamp_ms),
    [alertsA, floorTs]
  );
  const visibleAlertsB = useMemo(
    () =>
      alertsB
        .filter((a) => a.timestamp_ms <= floorTs)
        .sort((a, b) => b.timestamp_ms - a.timestamp_ms),
    [alertsB, floorTs]
  );

  const wqiGap =
    sessionA?.score_total != null && sessionB?.score_total != null
      ? Math.abs(Math.round(sessionB.score_total - sessionA.score_total))
      : null;
  const noOverlap = !comparison || comparison.deltas.length === 0;
  const duration =
    firstTimestamp != null && lastTimestamp != null ? lastTimestamp - firstTimestamp : 0;
  const elapsed =
    currentTimestamp != null && firstTimestamp != null ? currentTimestamp - firstTimestamp : 0;
  const pct = duration > 0 ? ((elapsed / duration) * 100).toFixed(1) : '0';

  if (loading) return <DemoSkeleton />;

  if (error) {
    const is404 =
      error.toLowerCase().includes('404') || error.toLowerCase().includes('not found');
    return (
      <div
        style={{
          background: C.bg,
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div
          style={{
            maxWidth: 480,
            background: C.surface,
            border: `1px solid ${C.border}`,
            borderRadius: 8,
            padding: 24,
          }}
        >
          <div
            style={{
              fontFamily: FONT_LABEL,
              fontSize: 14,
              fontWeight: 700,
              color: C.novice,
              marginBottom: 8,
            }}
          >
            {is404 ? 'Demo sessions not found' : 'Failed to load sessions'}
          </div>
          {is404 && (
            <div
              style={{
                fontFamily: FONT_DATA,
                fontSize: 11,
                color: C.textDim,
                marginBottom: 12,
              }}
            >
              Run POST /api/dev/seed-mock-sessions to create the expert/novice pair.
            </div>
          )}
          <div
            style={{
              fontFamily: FONT_DATA,
              fontSize: 11,
              color: C.textDim,
              marginBottom: 16,
            }}
          >
            {error}
          </div>
          <Link href="/dashboard" style={{ fontFamily: FONT_DATA, fontSize: 11, color: C.expert }}>
            Back to dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="demo-loaded"
      style={{
        background: C.bg,
        color: C.text,
        height: '100vh',
        display: 'grid',
        gridTemplateRows: '48px 1fr 32px',
        fontFamily: FONT_LABEL,
        overflow: 'hidden',
      }}
    >
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&display=swap'); * { box-sizing: border-box; margin: 0; padding: 0; }`}</style>

      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          borderBottom: `1px solid ${C.border}`,
          background: 'rgba(9,12,16,0.8)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'baseline' }}>
          <span
            style={{
              fontFamily: FONT_LABEL,
              fontSize: 18,
              fontWeight: 800,
              letterSpacing: '0.1em',
              color: C.white,
            }}
          >
            WELD
          </span>
          <span
            style={{
              fontFamily: FONT_LABEL,
              fontSize: 18,
              fontWeight: 300,
              letterSpacing: '0.1em',
              color: C.expert,
            }}
          >
            VIEW
          </span>
        </div>
        <div style={{ display: 'flex', gap: 32 }}>
          {[
            ['Session A', sessionIdA],
            ['Session B', sessionIdB],
          ].map(([l, v]) => (
            <div key={String(l)} style={{ textAlign: 'center' }}>
              <div
                style={{
                  fontSize: 7,
                  fontWeight: 600,
                  letterSpacing: '0.32em',
                  color: C.textDim,
                  textTransform: 'uppercase',
                  marginBottom: 1,
                }}
              >
                {l}
              </div>
              <div style={{ fontFamily: FONT_DATA, fontSize: 10, color: C.text }}>{v}</div>
            </div>
          ))}
        </div>
        <Link href="/dashboard" style={{ fontFamily: FONT_DATA, fontSize: 9, color: C.textDim, letterSpacing: '0.1em' }}>
          ← Dashboard
        </Link>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr 240px', overflow: 'hidden' }}>
        <div
          style={{
            borderRight: `1px solid ${C.border}`,
            background: 'rgba(13,17,23,0.9)',
            padding: '20px 18px',
            overflowY: 'auto',
          }}
        >
          <div
            style={{
              fontSize: 8,
              fontWeight: 600,
              letterSpacing: '0.32em',
              color: C.textDim,
              textTransform: 'uppercase',
              marginBottom: 18,
            }}
          >
            Parameter Comparison
          </div>
          <Sparkline
            noviceHistory={aHeatHist}
            expertHistory={bHeatHist}
            specMin={0.55}
            specMax={0.8}
            dataMin={0.5}
            dataMax={1.25}
            label="Heat Input"
            unit="kJ/mm"
          />
          <Sparkline
            noviceHistory={aAmpHist}
            expertHistory={bAmpHist}
            specMin={150}
            specMax={190}
            dataMin={130}
            dataMax={240}
            label="Amperage"
            unit="A"
          />
          <Sparkline
            noviceHistory={aAngleHist}
            expertHistory={bAngleHist}
            specMin={60}
            specMax={75}
            dataMin={55}
            dataMax={95}
            label="Torch Angle"
            unit="°"
          />

          <div style={{ marginTop: 4, paddingTop: 16, borderTop: `1px solid ${C.border}` }}>
            <div
              style={{
                fontSize: 8,
                fontWeight: 600,
                letterSpacing: '0.28em',
                color: C.textDim,
                textTransform: 'uppercase',
                marginBottom: 12,
              }}
            >
              Current Values
            </div>
            {(
              [
                [
                  'Heat',
                  currentFrameA?.heat_input_kj_per_mm?.toFixed(2) ?? '--',
                  currentFrameB?.heat_input_kj_per_mm?.toFixed(2) ?? '--',
                  'kJ/mm',
                ],
                [
                  'Amp',
                  currentFrameA?.amps != null ? String(Math.round(currentFrameA.amps)) : '--',
                  currentFrameB?.amps != null ? String(Math.round(currentFrameB.amps)) : '--',
                  'A',
                ],
                [
                  'Angle',
                  currentFrameA?.angle_degrees != null
                    ? String(Math.round(currentFrameA.angle_degrees))
                    : '--',
                  currentFrameB?.angle_degrees != null
                    ? String(Math.round(currentFrameB.angle_degrees))
                    : '--',
                  '°',
                ],
                [
                  'Temp',
                  currentTempA != null ? String(Math.round(currentTempA)) : '--',
                  currentTempB != null ? String(Math.round(currentTempB)) : '--',
                  '°C',
                ],
              ] as [string, string, string, string][]
            ).map(([l, av, bv, u]) => (
              <div
                key={l}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: 8,
                }}
              >
                <span
                  style={{
                    fontSize: 8,
                    letterSpacing: '0.2em',
                    color: C.textDim,
                    textTransform: 'uppercase',
                    width: 40,
                  }}
                >
                  {l}
                </span>
                <span style={{ fontFamily: FONT_DATA, fontSize: 11, color: C.novice }}>
                  {av}
                  <span style={{ fontSize: 8, color: 'rgba(255,69,69,0.4)', marginLeft: 2 }}>{u}</span>
                </span>
                <span style={{ fontSize: 7, color: C.textDim }}>vs</span>
                <span style={{ fontFamily: FONT_DATA, fontSize: 11, color: C.expert }}>
                  {bv}
                  <span style={{ fontSize: 8, color: 'rgba(0,229,160,0.4)', marginLeft: 2 }}>{u}</span>
                </span>
              </div>
            ))}
          </div>
        </div>

        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px 24px',
            gap: 0,
            position: 'relative',
          }}
        >
          {noOverlap && (
            <div
              style={{
                background: 'rgba(255,176,32,0.08)',
                border: '1px solid rgba(255,176,32,0.2)',
                borderRadius: 6,
                padding: '10px 16px',
                marginBottom: 16,
                fontSize: 10,
                color: C.amber,
                letterSpacing: '0.1em',
              }}
            >
              No overlapping frames. Sessions must share timestamps.
            </div>
          )}

          <div
            style={{
              display: 'flex',
              gap: 64,
              marginBottom: 28,
              alignItems: 'flex-end',
            }}
          >
            <WQIScore value={sessionA?.score_total} label="Session A" color={C.novice} />
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                paddingBottom: 16,
                gap: 6,
              }}
            >
              <div
                style={{
                  fontSize: 7,
                  fontWeight: 600,
                  letterSpacing: '0.3em',
                  color: C.textDim,
                  textTransform: 'uppercase',
                }}
              >
                Gap
              </div>
              <div
                style={{
                  fontFamily: FONT_DATA,
                  fontSize: 22,
                  color: 'rgba(255,255,255,0.2)',
                  letterSpacing: '-0.01em',
                }}
              >
                {wqiGap ?? '--'}
              </div>
              <div style={{ fontSize: 7, color: C.textDim, letterSpacing: '0.18em' }}>pts</div>
            </div>
            <WQIScore value={sessionB?.score_total} label="Session B" color={C.expert} />
          </div>

          <div style={{ position: 'relative' }}>
            <div
              style={{
                position: 'absolute',
                inset: -14,
                borderRadius: '50%',
                border: '1px solid rgba(255,255,255,0.05)',
                pointerEvents: 'none',
              }}
            />
            <div
              style={{
                position: 'absolute',
                inset: -6,
                borderRadius: '50%',
                border: '1px solid rgba(255,255,255,0.03)',
                pointerEvents: 'none',
              }}
            />
            <div
              style={{
                width: 'min(calc(100vh - 260px), 420px)',
                aspectRatio: '1/1',
                borderRadius: '50%',
                overflow: 'hidden',
                border: '1px solid rgba(255,255,255,0.08)',
                boxShadow:
                  '0 0 80px rgba(0,0,0,0.9), inset 0 0 40px rgba(0,0,0,0.5)',
              }}
            >
              <BeadDiffPlaceholder />
            </div>
          </div>

          {firstTimestamp != null &&
            lastTimestamp != null &&
            lastTimestamp > firstTimestamp && (
              <div style={{ width: '100%', maxWidth: 480, marginTop: 44 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <button
                      type="button"
                      onClick={() => setIsPlaying((p) => !p)}
                      disabled={noOverlap}
                      aria-label={isPlaying ? 'Pause playback' : 'Play playback'}
                      style={{
                        fontFamily: FONT_LABEL,
                        fontSize: 8,
                        fontWeight: 600,
                        letterSpacing: '0.22em',
                        textTransform: 'uppercase',
                        padding: '4px 10px',
                        background: 'rgba(255,255,255,0.06)',
                        border: `1px solid ${C.borderBright}`,
                        color: C.white,
                        cursor: 'pointer',
                        borderRadius: 2,
                        opacity: noOverlap ? 0.4 : 1,
                      }}
                    >
                      {isPlaying ? 'Pause' : 'Play'}
                    </button>
                    {[1, 2, 4].map((s) => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => setPlaybackSpeed(s)}
                        style={{
                          fontFamily: FONT_DATA,
                          fontSize: 8,
                          padding: '3px 7px',
                          background: playbackSpeed === s ? 'rgba(255,255,255,0.1)' : 'none',
                          border: `1px solid ${playbackSpeed === s ? C.borderBright : C.border}`,
                          color: playbackSpeed === s ? C.white : C.textDim,
                          cursor: 'pointer',
                          borderRadius: 2,
                        }}
                      >
                        {s}×
                      </button>
                    ))}
                  </div>
                  <span style={{ fontFamily: FONT_DATA, fontSize: 9, color: C.textDim }}>
                    {(elapsed / 1000).toFixed(2)}s / {(duration / 1000).toFixed(2)}s
                  </span>
                </div>
                <div
                  style={{
                    height: 1,
                    background: 'rgba(255,255,255,0.06)',
                    position: 'relative',
                    marginBottom: 4,
                  }}
                >
                  {[...alertsA, ...alertsB].map((a, i) => (
                    <div
                      key={i}
                      style={{
                        position: 'absolute',
                        left: `${((a.timestamp_ms - firstTimestamp) / duration) * 100}%`,
                        top: -2,
                        width: 1,
                        height: 5,
                        background:
                          (currentTimestamp ?? 0) >= a.timestamp_ms
                            ? C.novice
                            : 'rgba(255,69,69,0.2)',
                      }}
                    />
                  ))}
                  <div
                    style={{
                      height: '100%',
                      width: `${pct}%`,
                      background:
                        'linear-gradient(90deg, rgba(255,255,255,0.15), rgba(255,255,255,0.35))',
                      position: 'relative',
                      transition: 'width 0.08s linear',
                    }}
                  >
                    <div
                      style={{
                        position: 'absolute',
                        right: -4,
                        top: '50%',
                        transform: 'translateY(-50%)',
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: C.white,
                        boxShadow: '0 0 8px rgba(255,255,255,0.6)',
                      }}
                    />
                  </div>
                </div>
                <input
                  type="range"
                  min={firstTimestamp}
                  max={lastTimestamp}
                  step={FRAME_INTERVAL_MS}
                  value={currentTimestamp ?? firstTimestamp}
                  disabled={noOverlap}
                  onChange={(e) => {
                    setIsPlaying(false);
                    const val = Number(e.target.value);
                    setCurrentTimestamp(
                      Number.isFinite(val)
                        ? Math.max(firstTimestamp, Math.min(lastTimestamp, val))
                        : firstTimestamp
                    );
                  }}
                  style={{ width: '100%', accentColor: C.expert }}
                />
              </div>
            )}
        </div>

        <div
          style={{
            borderLeft: `1px solid ${C.border}`,
            background: 'rgba(13,17,23,0.9)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              padding: '16px 16px 12px',
              borderBottom: `1px solid ${C.border}`,
            }}
          >
            <div
              style={{
                fontSize: 8,
                fontWeight: 600,
                letterSpacing: '0.32em',
                color: C.textDim,
                textTransform: 'uppercase',
                marginBottom: 6,
              }}
            >
              Alert Feed
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span
                style={{
                  fontFamily: FONT_DATA,
                  fontSize: 9,
                  color: alertsErrorA ? C.amber : C.novice,
                }}
              >
                A: {alertsErrorA ? '—' : visibleAlertsA.length}
              </span>
              <span
                style={{
                  fontFamily: FONT_DATA,
                  fontSize: 9,
                  color: alertsErrorB ? C.amber : C.expert,
                }}
              >
                B: {alertsErrorB ? '—' : visibleAlertsB.length}
              </span>
            </div>
          </div>
          <div
            style={{
              flex: 1,
              overflow: 'hidden',
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
            }}
          >
            <div
              style={{
                borderRight: `1px solid ${C.border}`,
                padding: '10px 10px',
                overflowY: 'auto',
              }}
            >
              <div
                style={{
                  fontSize: 7,
                  fontWeight: 600,
                  letterSpacing: '0.28em',
                  color: C.textDim,
                  textTransform: 'uppercase',
                  marginBottom: 8,
                }}
              >
                Session A
              </div>
              {alertsErrorA ? (
                <div style={{ fontFamily: FONT_DATA, fontSize: 9, color: C.amber }}>
                  Alerts unavailable
                </div>
              ) : visibleAlertsA.length === 0 ? (
                <div style={{ fontFamily: FONT_DATA, fontSize: 9, color: C.textDim }}>
                  No alerts yet
                </div>
              ) : (
                visibleAlertsA.map((alert) => (
                  <AlertCard
                    key={`a-${alert.frame_index}-${alert.timestamp_ms}-${alert.rule_triggered}`}
                    alert={alert}
                    onSeek={() => {
                      setCurrentTimestamp(alert.timestamp_ms);
                      setIsPlaying(false);
                    }}
                  />
                ))
              )}
            </div>
            <div style={{ padding: '10px 10px', overflowY: 'auto' }}>
              <div
                style={{
                  fontSize: 7,
                  fontWeight: 600,
                  letterSpacing: '0.28em',
                  color: C.textDim,
                  textTransform: 'uppercase',
                  marginBottom: 8,
                }}
              >
                Session B
              </div>
              {alertsErrorB ? (
                <div style={{ fontFamily: FONT_DATA, fontSize: 9, color: C.amber }}>
                  Alerts unavailable
                </div>
              ) : visibleAlertsB.length === 0 ? (
                <div style={{ fontFamily: FONT_DATA, fontSize: 9, color: C.textDim }}>
                  No alerts yet
                </div>
              ) : (
                visibleAlertsB.map((alert) => (
                  <AlertCard
                    key={`b-${alert.frame_index}-${alert.timestamp_ms}-${alert.rule_triggered}`}
                    alert={alert}
                    onSeek={() => {
                      setCurrentTimestamp(alert.timestamp_ms);
                      setIsPlaying(false);
                    }}
                  />
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      <footer
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          borderTop: `1px solid ${C.border}`,
          background: 'rgba(9,12,16,0.8)',
        }}
      >
        <span
          style={{
            fontSize: 7.5,
            fontWeight: 400,
            letterSpacing: '0.22em',
            color: C.textDim,
            textTransform: 'uppercase',
          }}
        >
          WELDVIEW SYS v1.0
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <div
            style={{
              width: 5,
              height: 5,
              borderRadius: '50%',
              background: '#00e87a',
              boxShadow: '0 0 6px #00e87a',
            }}
          />
          <span
            style={{
              fontSize: 7.5,
              fontWeight: 600,
              letterSpacing: '0.28em',
              color: '#00e87a',
              textTransform: 'uppercase',
            }}
          >
            {isPlaying ? 'Replay Active' : 'Ready'}
          </span>
        </div>
        <span
          style={{
            fontSize: 7.5,
            fontWeight: 400,
            letterSpacing: '0.22em',
            color: C.textDim,
            textTransform: 'uppercase',
          }}
        >
          {sessionIdA} vs {sessionIdB}
        </span>
      </footer>
    </div>
  );
}

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
