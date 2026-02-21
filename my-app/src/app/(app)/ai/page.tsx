"use client";

import { useState, useEffect, useRef } from "react";

const SCENARIOS = [
  { id: 1, label: "On-Device Speed", query: "voltage is 28V, range 18-24" },
  { id: 2, label: "On-Device Speed", query: "angle 52 degrees, max 45" },
  { id: 3, label: "Cloud Coaching", query: "session WS-042 scored 41, why?" },
  {
    id: 4,
    label: "Agentic Chaining",
    query:
      "Analyze session WS-042 — check score, then parameters, then flag issues",
  },
  {
    id: 5,
    label: "Graceful Escalation",
    query: "wire_feed is 12, range 10-15",
  },
];

const SOURCE_COLORS: Record<string, string> = {
  "on-device": "#22c55e",
  cloud: "#3b82f6",
  "on-device→cloud": "#f59e0b",
  cloud_error: "#ef4444",
  offline: "#6b7280",
  error: "#ef4444",
};

const SOURCE_LABELS: Record<string, string> = {
  "on-device": "ON-DEVICE",
  cloud: "CLOUD",
  "on-device→cloud": "ESCALATED",
  cloud_error: "CLOUD ERROR",
  offline: "OFFLINE",
  error: "ERROR",
};

function getPrivacy(source: string): string {
  if (source === "on-device" || source.startsWith("on-device"))
    return "[ON-DEVICE] Sensor data never left the device.";
  if (source === "cloud")
    return "[CLOUD] Anonymized query only — no raw sensor values transmitted.";
  if (source === "offline") return "[OFFLINE] No network — canned response.";
  if (source === "cloud_error") return "[CLOUD ERROR] Gemini unavailable.";
  if (source === "on-device→cloud")
    return "[ON-DEVICE → CLOUD] Validation failed — escalated automatically.";
  return "";
}

interface ApiResult {
  source: string;
  text?: string;
  error?: string;
  function_calls?: { name: string; arguments?: Record<string, unknown> }[];
  total_time_ms?: number;
  latency_ms?: number;
  escalation_reason?: string;
}

export default function AIPage() {
  const [activeScenario, setActiveScenario] = useState<number | null>(null);
  const [isRunningAll, setIsRunningAll] = useState(false);
  const [completedScenarios, setCompletedScenarios] = useState<number[]>([]);
  const [scenarioResults, setScenarioResults] = useState<
    Record<number, ApiResult | null>
  >({});
  const [liveQuery, setLiveQuery] = useState("");
  const [liveResult, setLiveResult] = useState<ApiResult | null>(null);
  const [liveLoading, setLiveLoading] = useState(false);
  const [isOffline, setIsOffline] = useState(false);
  const [runningIndex, setRunningIndex] = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const fetchScenario = async (
    query: string,
    offline: boolean
  ): Promise<ApiResult> => {
    const res = await fetch("/api/ai/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, offline }),
    });
    const data = await res.json();
    if (!res.ok) {
      return {
        source: "error",
        error: data.detail || "Request failed",
        function_calls: [],
      };
    }
    return data;
  };

  const runScenario = async (scenario: (typeof SCENARIOS)[0]) => {
    const result = await fetchScenario(scenario.query, isOffline);
    setScenarioResults((prev) => ({ ...prev, [scenario.id]: result }));
    setActiveScenario(scenario.id);
  };

  const runAllScenarios = async () => {
    setIsRunningAll(true);
    setCompletedScenarios([]);
    setActiveScenario(null);
    setScenarioResults({});
    for (let i = 0; i < SCENARIOS.length; i++) {
      const s = SCENARIOS[i];
      setRunningIndex(i);
      setActiveScenario(s.id);
      const result = await fetchScenario(s.query, isOffline);
      setScenarioResults((prev) => ({ ...prev, [s.id]: result }));
      setCompletedScenarios((prev) => [...prev, s.id]);
      await new Promise((r) => setTimeout(r, 300));
    }
    setRunningIndex(null);
    setIsRunningAll(false);
  };

  const handleScenarioClick = (s: (typeof SCENARIOS)[0]) => {
    setActiveScenario(s.id);
    if (!scenarioResults[s.id]) {
      fetchScenario(s.query, isOffline).then((result) =>
        setScenarioResults((prev) => ({ ...prev, [s.id]: result }))
      );
    }
  };

  const handleLiveQuery = async () => {
    if (!liveQuery.trim()) return;
    setLiveLoading(true);
    setLiveResult(null);
    try {
      const res = await fetch("/api/ai/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: liveQuery.trim(), offline: isOffline }),
      });
      const data = await res.json();
      setLiveResult(data);
    } catch {
      setLiveResult({
        source: "error",
        text: "Could not reach backend. Make sure the server is running.",
        function_calls: [],
      });
    }
    setLiveLoading(false);
  };

  const scenario = activeScenario
    ? SCENARIOS.find((s) => s.id === activeScenario)
    : null;
  const result = scenario ? scenarioResults[scenario.id] : null;

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#080a0e",
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
        color: "#e2e8f0",
        padding: "0",
      }}
    >
      <div
        style={{
          borderBottom: "1px solid #1a2035",
          padding: "16px 32px",
          display: "flex",
          alignItems: "center",
          gap: "16px",
          background: "#0a0d14",
        }}
      >
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: "#ff6b1a",
            boxShadow: "0 0 8px #ff6b1a",
          }}
        />
        <span style={{ fontSize: 13, color: "#64748b", letterSpacing: "0.1em" }}>
          WARPSENSE
        </span>
        <span style={{ color: "#1a2035" }}>│</span>
        <span
          style={{ fontSize: 13, color: "#94a3b8", letterSpacing: "0.08em" }}
        >
          AI INFERENCE ENGINE
        </span>
        <div
          style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" }}
        >
          <div
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "#22c55e",
              boxShadow: "0 0 6px #22c55e",
            }}
          />
          <span style={{ fontSize: 11, color: "#22c55e" }}>SYSTEM ONLINE</span>
        </div>
      </div>

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "40px 32px" }}>
        <div
          style={{
            marginBottom: 48,
            borderLeft: "3px solid #ff6b1a",
            paddingLeft: 20,
          }}
        >
          <h1
            style={{
              fontSize: 36,
              fontWeight: 800,
              letterSpacing: "-0.02em",
              fontFamily: "'Barlow Condensed', sans-serif",
              color: "#f1f5f9",
              lineHeight: 1,
              marginBottom: 8,
            }}
          >
            ON-DEVICE WELDING AI
          </h1>
          <p style={{ fontSize: 13, color: "#64748b", letterSpacing: "0.06em" }}>
            FunctionGemma 270M · Cactus Runtime · Gemini Cloud Fallback
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 1,
            marginBottom: 40,
            background: "#1a2035",
            border: "1px solid #1a2035",
            borderRadius: 4,
            overflow: "hidden",
          }}
        >
          {[
            { label: "MODEL", value: "270M", sub: "params" },
            { label: "ON-DEVICE LATENCY", value: "<100", sub: "ms" },
            { label: "ROUTING", value: "SMART", sub: "interrogative gate" },
            { label: "OFFLINE", value: "YES", sub: "zero network" },
          ].map((stat) => (
            <div
              key={stat.label}
              style={{
                background: "#0a0d14",
                padding: "20px 24px",
              }}
            >
              <div
                style={{
                  fontSize: 10,
                  color: "#475569",
                  letterSpacing: "0.12em",
                  marginBottom: 6,
                }}
              >
                {stat.label}
              </div>
              <div
                style={{
                  fontSize: 28,
                  fontWeight: 700,
                  color: "#ff6b1a",
                  lineHeight: 1,
                }}
              >
                {stat.value}
              </div>
              <div style={{ fontSize: 11, color: "#475569", marginTop: 4 }}>
                {stat.sub}
              </div>
            </div>
          ))}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          <div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: 16,
              }}
            >
              <span
                style={{
                  fontSize: 11,
                  color: "#475569",
                  letterSpacing: "0.12em",
                }}
              >
                DEMO SCENARIOS
              </span>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <button
                  onClick={() => setIsOffline((v) => !v)}
                  style={{
                    background: isOffline ? "#374151" : "transparent",
                    border: "1px solid",
                    borderColor: isOffline ? "#6b7280" : "#1e2d40",
                    color: isOffline ? "#9ca3af" : "#475569",
                    padding: "4px 10px",
                    fontSize: 10,
                    letterSpacing: "0.1em",
                    cursor: "pointer",
                    borderRadius: 2,
                  }}
                >
                  {isOffline ? "OFFLINE ON" : "OFFLINE OFF"}
                </button>
                <button
                  onClick={runAllScenarios}
                  disabled={isRunningAll}
                  style={{
                    background: isRunningAll ? "#1a2035" : "#ff6b1a",
                    border: "none",
                    color: isRunningAll ? "#475569" : "#080a0e",
                    padding: "6px 14px",
                    fontSize: 11,
                    fontWeight: 700,
                    letterSpacing: "0.1em",
                    cursor: isRunningAll ? "not-allowed" : "pointer",
                    borderRadius: 2,
                    fontFamily: "inherit",
                  }}
                >
                  {isRunningAll ? "RUNNING..." : "▶ RUN ALL"}
                </button>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {SCENARIOS.map((s, i) => {
                const isActive = activeScenario === s.id;
                const isDone = completedScenarios.includes(s.id);
                const isRunning = runningIndex === i;
                const res = scenarioResults[s.id];
                const source = res?.source ?? "on-device";
                const sourceColor = SOURCE_COLORS[source] || "#64748b";

                return (
                  <div
                    key={s.id}
                    onClick={() => handleScenarioClick(s)}
                    style={{
                      border: "1px solid",
                      borderColor: isActive ? "#ff6b1a" : "#1a2035",
                      background: isActive ? "#0f1520" : "#0a0d14",
                      padding: "14px 16px",
                      cursor: "pointer",
                      borderRadius: 3,
                      transition: "all 0.15s",
                      position: "relative",
                      overflow: "hidden",
                    }}
                  >
                    {isRunning && (
                      <div
                        style={{
                          position: "absolute",
                          top: 0,
                          left: 0,
                          height: 2,
                          background: "#ff6b1a",
                          animation: "progress 1.2s linear",
                          width: "100%",
                        }}
                      />
                    )}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        marginBottom: 6,
                      }}
                    >
                      <span
                        style={{
                          fontSize: 10,
                          color: isDone ? "#22c55e" : "#334155",
                          fontWeight: 700,
                        }}
                      >
                        {isDone ? "✓" : `0${s.id}`}
                      </span>
                      <span
                        style={{
                          fontSize: 10,
                          color: sourceColor,
                          background: sourceColor + "15",
                          padding: "2px 7px",
                          borderRadius: 2,
                          letterSpacing: "0.08em",
                        }}
                      >
                        {SOURCE_LABELS[source]}
                      </span>
                      <span
                        style={{
                          fontSize: 10,
                          color: "#475569",
                          marginLeft: "auto",
                        }}
                      >
                        {s.label}
                      </span>
                    </div>
                    <div
                      style={{
                        fontSize: 12,
                        color: "#94a3b8",
                        fontFamily: "inherit",
                      }}
                    >
                      &quot;{s.query}&quot;
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div>
            <div
              style={{
                fontSize: 11,
                color: "#475569",
                letterSpacing: "0.12em",
                marginBottom: 16,
              }}
            >
              OUTPUT
            </div>

            {scenario && result ? (
              <div
                style={{
                  border: "1px solid #1a2035",
                  borderRadius: 3,
                  overflow: "hidden",
                  background: "#0a0d14",
                }}
              >
                <div
                  style={{
                    padding: "10px 16px",
                    background: "#0f1520",
                    borderBottom: "1px solid #1a2035",
                    fontSize: 11,
                    color: SOURCE_COLORS[result.source] || "#64748b",
                    letterSpacing: "0.06em",
                  }}
                >
                  {getPrivacy(result.source)}
                </div>

                <div style={{ padding: 20 }}>
                  <div
                    style={{
                      display: "flex",
                      gap: 16,
                      marginBottom: 20,
                      flexWrap: "wrap",
                    }}
                  >
                    <div>
                      <div
                        style={{
                          fontSize: 10,
                          color: "#334155",
                          marginBottom: 4,
                        }}
                      >
                        SOURCE
                      </div>
                      <div
                        style={{
                          fontSize: 13,
                          fontWeight: 700,
                          color:
                            SOURCE_COLORS[result.source] || "#f1f5f9",
                        }}
                      >
                        {result.source}
                      </div>
                    </div>
                    <div>
                      <div
                        style={{
                          fontSize: 10,
                          color: "#334155",
                          marginBottom: 4,
                        }}
                      >
                        TIME
                      </div>
                      <div
                        style={{
                          fontSize: 13,
                          fontWeight: 700,
                          color: "#f1f5f9",
                        }}
                      >
                        {result.total_time_ms ?? result.latency_ms ?? 0}ms
                      </div>
                    </div>
                    {result.escalation_reason && (
                      <div>
                        <div
                          style={{
                            fontSize: 10,
                            color: "#334155",
                            marginBottom: 4,
                          }}
                        >
                          ESCALATION
                        </div>
                        <div
                          style={{ fontSize: 11, color: "#f59e0b" }}
                        >
                          {result.escalation_reason}
                        </div>
                      </div>
                    )}
                  </div>

                  {result.function_calls &&
                    result.function_calls.length > 0 && (
                      <div style={{ marginBottom: 16 }}>
                        <div
                          style={{
                            fontSize: 10,
                            color: "#334155",
                            marginBottom: 8,
                          }}
                        >
                          TOOL CALL
                        </div>
                        <div
                          style={{
                            background: "#0d1420",
                            border: "1px solid #1a2d20",
                            borderRadius: 3,
                            padding: "12px 14px",
                          }}
                        >
                          {result.function_calls.map((fc, idx) => (
                            <div
                              key={idx}
                              style={{
                                fontSize: 12,
                                color: "#22c55e",
                                marginBottom:
                                  idx < result.function_calls!.length - 1
                                    ? 8
                                    : 0,
                              }}
                            >
                              {fc.name}
                              {fc.arguments &&
                                Object.keys(fc.arguments).length > 0 && (
                                  <>
                                    {" "}
                                    (
                                    {Object.entries(fc.arguments).map(
                                      ([k, v]) => (
                                        <span
                                          key={k}
                                          style={{
                                            fontSize: 11,
                                            color: "#64748b",
                                          }}
                                        >
                                          {k}: {String(v)}{" "}
                                        </span>
                                      )
                                    )}
                                    )
                                  </>
                                )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                  {(result.text || result.error) && (
                    <div>
                      <div
                        style={{
                          fontSize: 10,
                          color: "#334155",
                          marginBottom: 8,
                        }}
                      >
                        {result.error ? "ERROR" : "RESPONSE"}
                      </div>
                      <div
                        style={{
                          background: "#0d1420",
                          border: "1px solid #1a2035",
                          borderRadius: 3,
                          padding: "12px 14px",
                          fontSize: 12,
                          color: result.error ? "#ef4444" : "#94a3b8",
                          lineHeight: 1.7,
                        }}
                      >
                        {result.error || result.text}
                      </div>
                    </div>
                  )}

                  {!result.text &&
                    !result.error &&
                    (!result.function_calls ||
                      result.function_calls.length === 0) && (
                      <div
                        style={{
                          fontSize: 11,
                          color: "#64748b",
                          fontStyle: "italic",
                        }}
                      >
                        No tool calls or text response.
                      </div>
                    )}
                </div>
              </div>
            ) : scenario && !result ? (
              <div
                style={{
                  border: "1px solid #1a2035",
                  borderRadius: 3,
                  height: 300,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#475569",
                  fontSize: 12,
                  letterSpacing: "0.1em",
                }}
              >
                Loading...
              </div>
            ) : (
              <div
                style={{
                  border: "1px solid #1a2035",
                  borderRadius: 3,
                  height: 300,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#1e2d40",
                  fontSize: 12,
                  letterSpacing: "0.1em",
                }}
              >
                SELECT A SCENARIO OR RUN ALL
              </div>
            )}
          </div>
        </div>

        <div
          style={{
            marginTop: 40,
            borderTop: "1px solid #1a2035",
            paddingTop: 32,
          }}
        >
          <div
            style={{
              fontSize: 11,
              color: "#475569",
              letterSpacing: "0.12em",
              marginBottom: 16,
            }}
          >
            LIVE QUERY — POST /api/ai/analyze
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <input
              ref={inputRef}
              value={liveQuery}
              onChange={(e) => setLiveQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLiveQuery()}
              placeholder="voltage is 28V, range 18-24..."
              style={{
                flex: 1,
                background: "#0a0d14",
                border: "1px solid #1a2035",
                borderRadius: 3,
                padding: "10px 14px",
                fontSize: 13,
                color: "#e2e8f0",
                fontFamily: "inherit",
                outline: "none",
              }}
            />
            <button
              onClick={handleLiveQuery}
              disabled={liveLoading}
              style={{
                background: liveLoading ? "#1a2035" : "#ff6b1a",
                border: "none",
                color: liveLoading ? "#475569" : "#080a0e",
                padding: "10px 20px",
                fontSize: 12,
                fontWeight: 700,
                letterSpacing: "0.1em",
                cursor: liveLoading ? "not-allowed" : "pointer",
                borderRadius: 3,
                fontFamily: "inherit",
              }}
            >
              {liveLoading ? "..." : "SEND"}
            </button>
          </div>

          {liveResult && (
            <div
              style={{
                marginTop: 12,
                background: "#0a0d14",
                border: "1px solid #1a2035",
                borderRadius: 3,
                padding: 16,
              }}
            >
              <div
                style={{
                  display: "flex",
                  gap: 16,
                  marginBottom: 12,
                }}
              >
                <span
                  style={{
                    fontSize: 12,
                    color:
                      SOURCE_COLORS[liveResult.source] || "#64748b",
                    fontWeight: 700,
                  }}
                >
                  {liveResult.source?.toUpperCase()}
                </span>
                {(liveResult.total_time_ms ?? liveResult.latency_ms) && (
                  <span style={{ fontSize: 12, color: "#64748b" }}>
                    {Math.round(
                      liveResult.total_time_ms ?? liveResult.latency_ms ?? 0
                    )}
                    ms
                  </span>
                )}
              </div>
              {liveResult.function_calls &&
                liveResult.function_calls.length > 0 && (
                  <div style={{ marginBottom: 10 }}>
                    {liveResult.function_calls.map((fc, i) => (
                      <div
                        key={i}
                        style={{ fontSize: 12, color: "#22c55e" }}
                      >
                        {fc.name}(
                        {JSON.stringify(fc.arguments || {})})
                      </div>
                    ))}
                  </div>
                )}
              {liveResult.text && (
                <div
                  style={{
                    fontSize: 12,
                    color: "#94a3b8",
                    lineHeight: 1.7,
                  }}
                >
                  {liveResult.text}
                </div>
              )}
              {liveResult.error && (
                <div style={{ fontSize: 12, color: "#ef4444" }}>
                  {liveResult.error}
                </div>
              )}
            </div>
          )}
        </div>

        <div
          style={{
            marginTop: 40,
            padding: "16px 20px",
            background: "#0a0d14",
            border: "1px solid #1a2035",
            borderRadius: 3,
            display: "flex",
            gap: 32,
            flexWrap: "wrap",
          }}
        >
          {[
            {
              label: "ON-DEVICE",
              desc: "FunctionGemma 270M via Cactus runtime. <100ms. Sensor data never transmitted.",
            },
            {
              label: "ROUTING",
              desc: "Interrogative gate: why/explain → cloud. Measurement queries → on-device.",
            },
            {
              label: "ESCALATION",
              desc: "Enum validation failure triggers automatic on-device→cloud escalation.",
            },
            {
              label: "OFFLINE",
              desc: "Zero network fallback. Graceful degradation for shop floor connectivity.",
            },
          ].map((item) => (
            <div key={item.label} style={{ flex: "1 1 180px" }}>
              <div
                style={{
                  fontSize: 10,
                  color: "#ff6b1a",
                  letterSpacing: "0.1em",
                  marginBottom: 4,
                }}
              >
                {item.label}
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: "#475569",
                  lineHeight: 1.6,
                }}
              >
                {item.desc}
              </div>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        @keyframes progress {
          from { width: 0% }
          to { width: 100% }
        }
        input::placeholder { color: #334155; }
        * { box-sizing: border-box; }
      `}</style>
    </div>
  );
}
