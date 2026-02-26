/**
 * /live — iPad companion PWA page.
 * Polls warp-risk every 5s. No WebGL. Min 48px touch targets.
 */
"use client";
import React, { Suspense, useEffect, useState, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { LiveStatusLED } from "@/components/live/LiveStatusLED";
import { LiveAngleIndicator } from "@/components/welding/LiveAngleIndicator";
import { WarpRiskResponse } from "@/types/prediction";
import { RiskLevel } from "@/types/shared";
import { fetchWarpRisk } from "@/lib/api";
import { logError } from "@/lib/logger";

const POLL_INTERVAL_MS = 5000;
const DEFAULT_SESSION = "sess_novice_001";

function LivePageContent() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session") ?? DEFAULT_SESSION;

  const [risk, setRisk] = useState<WarpRiskResponse | null>(null);
  const [angle] = useState<number>(45);
  const [lastAlert, setLastAlert] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const poll = async () => {
    try {
      const data = await fetchWarpRisk(sessionId);
      setRisk(data);
      setConnected(true);
      if (data.risk_level !== "ok") {
        setLastAlert(`Warp risk: ${Math.round(data.probability * 100)}% at ${new Date().toLocaleTimeString()}`);
      }
    } catch (err) {
      logError("LivePage.poll", err);
      setConnected(false);
    }
  };

  useEffect(() => {
    poll();
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [sessionId]);

  const riskLevel: RiskLevel = risk?.risk_level ?? "ok";

  return (
    <div className="min-h-screen bg-neutral-950 flex flex-col p-4 gap-4" style={{ touchAction: "manipulation" }}>
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-white tracking-widest uppercase">WarpSense Live</h1>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${connected ? "bg-green-500" : "bg-red-500"}`} />
          <span className="text-xs text-neutral-500">{connected ? "Connected" : "Disconnected"}</span>
          <span className="text-xs text-neutral-600 ml-2">{sessionId}</span>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-3 gap-4">
        <div className="col-span-2 flex flex-col gap-4">
          <LiveStatusLED riskLevel={riskLevel} height={120} />
          <div className="flex-1 flex items-center justify-center bg-neutral-900 rounded-xl">
            <LiveAngleIndicator currentAngle={angle} riskLevel={riskLevel} size={240} />
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <div className="bg-neutral-900 rounded-xl p-4 text-center">
            <p className="text-xs text-neutral-500 uppercase tracking-widest mb-1">Warp Risk</p>
            <p className={`text-5xl font-black tabular-nums ${
              riskLevel === "critical" ? "text-red-400" :
              riskLevel === "warning"  ? "text-amber-400" : "text-cyan-400"
            }`}>
              {risk ? `${Math.round(risk.probability * 100)}%` : "—"}
            </p>
          </div>

          {lastAlert && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3">
              <p className="text-xs text-amber-400 font-semibold uppercase tracking-wider mb-1">Last Alert</p>
              <p className="text-xs text-amber-300">{lastAlert}</p>
              <button
                onClick={() => setLastAlert(null)}
                className="mt-2 text-xs text-neutral-500 hover:text-neutral-300 min-h-[48px] w-full text-left"
              >
                Dismiss
              </button>
            </div>
          )}

          <div className="bg-neutral-900 rounded-xl p-4 mt-auto">
            <p className="text-xs text-neutral-500 uppercase tracking-widest mb-2">Session</p>
            <p className="text-sm text-white font-mono">{sessionId}</p>
            <p className="text-xs text-neutral-600 mt-1">Updated {new Date().toLocaleTimeString()}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LivePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-neutral-950 flex items-center justify-center">
          <div className="text-sm text-neutral-500">Loading...</div>
        </div>
      }
    >
      <LivePageContent />
    </Suspense>
  );
}
