'use client';

/**
 * Real-time alert demo: NS thermal bar (±30°C), travel angle gauge, alert panel.
 * Connects to WebSocket at backend /ws/realtime-alerts.
 * Fetches GET /config/thresholds for gauge color bands.
 */

import { useEffect, useState } from 'react';
import { getRuleLabel } from '@/lib/alert-labels';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_BASE = API_BASE.replace(/^http/, 'ws');

interface Thresholds {
  angle_deviation_warning?: number;
  angle_deviation_critical?: number;
}

interface FrameMsg {
  frame_index: number;
  ns_asymmetry: number;
  travel_angle_degrees: number;
}

interface AlertMsg {
  frame_index: number;
  rule_triggered: string;
  severity: string;
  message: string;
  correction: string;
  timestamp_ms: number;
}

type WsMsg = FrameMsg | AlertMsg;

function isAlertMsg(m: WsMsg): m is AlertMsg {
  return 'rule_triggered' in m && 'correction' in m;
}

/** NS thermal bar: ±30°C range, MAX labels when saturated, 80ms transition. */
function NSThermalBar({ value }: { value: number }) {
  const clipped = Math.max(-30, Math.min(30, value));
  const isMax = value > 30;
  const isMin = value < -30;
  const pct = (Math.abs(clipped) / 30) * 50;
  return (
    <div className="flex flex-col gap-1">
      <div className="relative h-8 bg-zinc-200 dark:bg-zinc-700 rounded overflow-hidden">
        <div className="absolute inset-y-0 left-1/2 w-0.5 bg-zinc-500 -ml-px z-10" />
        {clipped >= 0 && (
          <div
            className="absolute top-1 bottom-1 left-1/2 rounded-r bg-red-500 transition-all duration-[80ms] ease-out"
            style={{ width: `${pct}%`, marginLeft: 0 }}
          />
        )}
        {clipped < 0 && (
          <div
            className="absolute top-1 bottom-1 right-1/2 rounded-l bg-blue-500 transition-all duration-[80ms] ease-out"
            style={{ width: `${pct}%`, marginRight: 0 }}
          />
        )}
      </div>
      <div className="flex justify-between text-xs">
        {isMin && <span className="text-blue-600 font-medium">MAX</span>}
        <span className={isMin || isMax ? 'invisible' : ''}>{value.toFixed(1)}°C</span>
        {isMax && <span className="text-red-600 font-medium">MAX</span>}
      </div>
    </div>
  );
}

/** Travel angle gauge: center 12°, color from thresholds. */
function TravelAngleGauge({
  angle,
  thresholds,
}: {
  angle: number;
  thresholds: Thresholds;
}) {
  const warning = thresholds.angle_deviation_warning ?? 6;
  const critical = thresholds.angle_deviation_critical ?? 10;
  const dev = Math.abs(angle - 12);
  const color =
    dev >= critical ? 'red' : dev >= warning ? 'yellow' : 'green';
  const rotation = (angle - 12) * 3;
  return (
    <div className="flex flex-col items-center gap-2">
      <div
        className="w-24 h-24 rounded-full border-4 flex items-center justify-center"
        style={{
          borderColor: color === 'red' ? '#dc2626' : color === 'yellow' ? '#eab308' : '#22c55e',
        }}
      >
        <div
          className="w-1 h-10 bg-zinc-800 dark:bg-zinc-200 origin-bottom"
          style={{ transform: `rotate(${rotation}deg)` }}
        />
      </div>
      <div className="text-xs text-zinc-500">{angle.toFixed(1)}° (nominal 12°)</div>
    </div>
  );
}

/** Alert panel: flash on alert, fade after 2s. */
function AlertPanel({ alert, count }: { alert: AlertMsg | null; count: number }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (alert) {
      setVisible(true);
      const t = setTimeout(() => setVisible(false), 2000);
      return () => clearTimeout(t);
    }
  }, [alert?.timestamp_ms]);
  if (!alert && count === 0) return null;
  return (
    <div
      className={`w-full py-3 px-4 rounded transition-opacity duration-300 ${
        visible ? 'opacity-100 bg-red-100 dark:bg-red-900/50' : 'opacity-0'
      }`}
    >
      {alert && (
        <>
          <div className="font-medium text-red-800 dark:text-red-200">{alert.correction}</div>
          <div className="text-sm text-red-600 dark:text-red-400">
            {getRuleLabel(alert.rule_triggered)} · {alert.severity}
          </div>
        </>
      )}
      <div className="text-xs text-zinc-500 mt-1">Alerts: {count}</div>
    </div>
  );
}

export default function RealtimePage() {
  const [thresholds, setThresholds] = useState<Thresholds>({});
  const [nsAsymmetry, setNsAsymmetry] = useState(0);
  const [travelAngle, setTravelAngle] = useState(12);
  const [lastAlert, setLastAlert] = useState<AlertMsg | null>(null);
  const [alertCount, setAlertCount] = useState(0);
  const [wsStatus, setWsStatus] = useState<'connecting' | 'open' | 'closed'>('connecting');

  useEffect(() => {
    fetch(`${API_BASE}/config/thresholds`)
      .then((r) => r.json())
      .then(setThresholds)
      .catch(() => {});
  }, []);

  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/realtime-alerts`);
    ws.onopen = () => setWsStatus('open');
    ws.onclose = () => setWsStatus('closed');
    ws.onmessage = (e) => {
      try {
        const msg: WsMsg = JSON.parse(e.data);
        if (isAlertMsg(msg)) {
          setLastAlert(msg);
          setAlertCount((c) => c + 1);
        } else {
          setNsAsymmetry(msg.ns_asymmetry);
          setTravelAngle(msg.travel_angle_degrees);
        }
      } catch {}
    };
    return () => ws.close();
  }, []);

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 p-6">
      <h1 className="text-xl font-semibold mb-4">Real-time Alert Demo</h1>
      <p className="text-sm text-zinc-500 mb-4">
        Run: <code className="bg-zinc-200 dark:bg-zinc-800 px-1 rounded">python -m scripts.simulate_realtime --mode novice --output websocket --loop</code>
      </p>
      <div className="text-xs text-zinc-500 mb-4">
        WebSocket: {wsStatus}
      </div>
      <div className="flex flex-col gap-6 max-w-md">
        <div className="bg-white dark:bg-zinc-900 rounded-lg border p-4">
          <h2 className="text-sm font-medium mb-2">NS Thermal Bar (±30°C)</h2>
          <NSThermalBar value={nsAsymmetry} />
        </div>
        <div className="bg-white dark:bg-zinc-900 rounded-lg border p-4">
          <h2 className="text-sm font-medium mb-2">Travel Angle Gauge</h2>
          <TravelAngleGauge angle={travelAngle} thresholds={thresholds} />
        </div>
        <div className="bg-white dark:bg-zinc-900 rounded-lg border p-4">
          <h2 className="text-sm font-medium mb-2">Alert Panel</h2>
          <AlertPanel alert={lastAlert} count={alertCount} />
        </div>
      </div>
    </div>
  );
}
