/**
 * PDF layout component for welder session report.
 * Supervisor/investor-grade rejection document.
 *
 * Uses @react-pdf/renderer — PDF-native components, no DOM or canvas capture.
 * Renders on server in Next.js API route.
 */

import {
  Document,
  Page,
  View,
  Text,
  StyleSheet,
} from "@react-pdf/renderer";

const COLORS = {
  BG: "#0d0f1a",
  PANEL: "#141728",
  BORDER: "#1e2236",
  ACCENT: "#4d7cfe",
  TEXT_PRI: "#e8eaf0",
  TEXT_SEC: "#8b91a8",
  GREEN: "#22c55e",
  RED: "#ef4444",
  AMBER: "#f59e0b",
} as const;

/** Sanitize text for PDF rendering. Strips control chars, zero-width, RTL-override. */
function sanitizeText(str: string): string {
  if (typeof str !== "string") return "";
  return str
    .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g, "")
    .replace(/[\u200b-\u200d\u2060\ufeff]/g, "")
    .replace(/[\u202a-\u202e\u2066-\u2069]/g, "")
    .replace(/</g, "‹")
    .replace(/>/g, "›");
}

/** Format dollar amount without relying on locale — safe for Node PDF renderer. */
function formatCost(n: number): string {
  return "$" + Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function dispositionColor(d: string | null | undefined): string {
  if (d === "PASS") return COLORS.GREEN;
  if (d === "CONDITIONAL") return COLORS.AMBER;
  return COLORS.RED;
}

function dispositionLabel(d: string | null | undefined): string {
  if (d === "PASS") return "PASS";
  if (d === "CONDITIONAL") return "CONDITIONAL";
  return "REWORK REQUIRED";
}

/**
 * Map backend agent_name values (PascalCase, from specialists.py) to display labels.
 * Actual values confirmed from backend/agent/specialists.py:
 *   "ThermalAgent", "GeometryAgent", "ProcessStabilityAgent"
 */
function agentDisplayLabel(name: string): string {
  if (name === "ThermalAgent") return "Thermal Analysis";
  if (name === "GeometryAgent") return "Geometry Analysis";
  if (name === "ProcessStabilityAgent") return "Process Analysis";
  return sanitizeText(name);
}

const styles = StyleSheet.create({
  page: {
    backgroundColor: COLORS.BG,
    padding: 40,
    fontFamily: "Helvetica",
  },
  topBar: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    minHeight: 80,
    backgroundColor: COLORS.PANEL,
    marginHorizontal: -40,
    marginTop: -40,
    paddingHorizontal: 40,
    paddingTop: 16,
    paddingBottom: 14,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.BORDER,
  },
  logo: { fontSize: 14, color: COLORS.ACCENT, fontWeight: "bold", marginBottom: 2 },
  tagline: { fontSize: 8, color: COLORS.TEXT_SEC, marginBottom: 6 },
  welderName: { fontSize: 18, color: COLORS.TEXT_PRI, fontWeight: "bold", marginBottom: 4 },
  metaLine: { fontSize: 9, color: COLORS.TEXT_SEC },
  scoreCircle: {
    width: 56,
    height: 56,
    borderRadius: 28,
    borderWidth: 2,
    borderColor: COLORS.ACCENT,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 6,
  },
  scoreText: { fontSize: 18, color: COLORS.ACCENT, fontWeight: "bold" },
  scoreDenom: { fontSize: 7, color: COLORS.TEXT_SEC },
  sectionTitle: {
    fontSize: 9,
    color: COLORS.TEXT_SEC,
    textTransform: "uppercase",
    letterSpacing: 2,
    marginBottom: 8,
  },
  panel: {
    marginTop: 16,
    padding: 14,
    backgroundColor: COLORS.PANEL,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: COLORS.BORDER,
  },
  footer: {
    position: "absolute",
    bottom: 30,
    left: 40,
    right: 40,
    borderTopWidth: 1,
    borderTopColor: COLORS.BORDER,
    paddingTop: 10,
    flexDirection: "row",
    justifyContent: "space-between",
  },
  footerText: { fontSize: 8, color: COLORS.TEXT_SEC },
});

export interface WelderReportPDFProps {
  panelId: string;
  panelName: string;
  welderAttribution: string | null;
  score: { total: number };
  feedback: {
    summary: string;
    feedback_items: Array<{
      message: string;
      severity: string;
      suggestion?: string | null;
    }>;
  };
  narrative?: string | null;
  rework_cost_usd?: number | null;
  disposition?: string | null;
  agentInsights?: Array<{
    agent_name: string;
    disposition?: string;
    root_cause?: string;
    corrective_actions?: string[];
    disposition_rationale?: string | null;
    consequence?: string | null;
    reject_label?: string | null;
  }> | null;
  sessionDate?: string | null;
  duration?: string | null;
  station?: string | null;
}

export function toWelderName(v: unknown): string {
  if (typeof v === "string" && v.trim().length > 0) return v.trim();
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return "Unknown";
}

export function WelderReportPDF({
  panelId: _panelId,
  panelName,
  welderAttribution,
  score,
  feedback,
  narrative,
  rework_cost_usd,
  disposition,
  agentInsights,
  sessionDate,
  duration,
  station,
}: WelderReportPDFProps) {
  const displayPanelName = sanitizeText(panelName || "Panel");
  const displayAttribution = welderAttribution ? sanitizeText(welderAttribution) : null;
  const totalScore = Math.round(score?.total ?? 0);
  const cost = rework_cost_usd ?? 0;
  const costColor =
    cost === 0 ? COLORS.GREEN : cost <= 1800 ? COLORS.AMBER : COLORS.RED;
  const dispColor = dispositionColor(disposition);
  const dispLabel = dispositionLabel(disposition);

  const metaParts: string[] = [];
  if (sessionDate) metaParts.push(sessionDate);
  if (station) metaParts.push(station);
  if (duration) metaParts.push(duration);
  const metaLine =
    metaParts.length > 0
      ? `Session Report · ${metaParts.join(" · ")}`
      : "Session Report";

  /**
   * Build insight map keyed by agent_name (PascalCase).
   * AGENT_ORDER matches the canonical values from backend/agent/specialists.py:
   *   for agent_name in ["ThermalAgent", "GeometryAgent", "ProcessStabilityAgent"]
   */
  const AGENT_ORDER = ["ThermalAgent", "GeometryAgent", "ProcessStabilityAgent"];
  interface PdfAgentInsight {
    disposition?: string;
    root_cause?: string;
    disposition_rationale?: string | null;
    consequence?: string | null;
    reject_label?: string | null;
    corrective_actions?: string[];
  }
  const insightMap: Record<string, PdfAgentInsight> = {};
  for (const row of agentInsights ?? []) {
    insightMap[row.agent_name] = {
      disposition:           row.disposition,
      root_cause:            row.root_cause,
      disposition_rationale: row.disposition_rationale,
      consequence:           row.consequence,
      reject_label:          row.reject_label,
      corrective_actions:    row.corrective_actions,
    };
  }

  return (
    <Document>
      <Page size="LETTER" style={styles.page}>
        {/* TOP BAR */}
        <View style={styles.topBar}>
          <View style={{ flex: 1 }}>
            <Text style={styles.logo}>WARPSENSE</Text>
            <Text style={styles.tagline}>Quality Intelligence Platform</Text>
            <Text style={styles.welderName}>{displayPanelName}</Text>
            {displayAttribution != null && (
              <Text style={{ fontSize: 9, color: COLORS.TEXT_SEC, marginBottom: 2 }}>
                Worked by: {displayAttribution}
              </Text>
            )}
            <Text style={styles.metaLine}>{metaLine}</Text>
          </View>
          <View style={{ alignItems: "center" }}>
            <View style={styles.scoreCircle}>
              <Text style={styles.scoreText}>{totalScore}</Text>
              <Text style={styles.scoreDenom}>/ 100</Text>
            </View>
            <View
              style={{
                paddingHorizontal: 8,
                paddingVertical: 3,
                borderRadius: 4,
                backgroundColor: dispColor,
                alignItems: "center",
              }}
            >
              <Text style={{ fontSize: 7, color: "#fff", fontWeight: "bold" }}>
                {dispLabel}
              </Text>
            </View>
          </View>
        </View>

        {/* COMPACT REWORK COST — secondary to the score hero */}
        {cost > 0 && (
          <View style={{ marginTop: 8, flexDirection: "row", alignItems: "center", gap: 8 }}>
            <Text style={{ fontSize: 9, color: COLORS.TEXT_SEC, textTransform: "uppercase", letterSpacing: 1 }}>
              Est. Rework Cost:
            </Text>
            <Text style={{ fontSize: 11, color: costColor, fontWeight: "bold" }}>
              {formatCost(cost)}
            </Text>
          </View>
        )}

        {/* AGENT FINDINGS — stacked narrative blocks (one per agent) */}
        <View style={{ marginTop: 16 }}>
          <Text style={styles.sectionTitle}>Agent Findings</Text>
          {AGENT_ORDER.map((agentKey) => {
            const insight = insightMap[agentKey];
            const agentDisp = insight?.disposition;
            const isRejected = agentDisp != null && agentDisp !== "PASS";

            if (!isRejected) {
              // Passing agent — compact single row with green PASS badge
              return (
                <View
                  key={agentKey}
                  style={{
                    flexDirection: "row",
                    alignItems: "center",
                    marginBottom: 6,
                    padding: 6,
                    backgroundColor: COLORS.PANEL,
                    borderRadius: 4,
                    borderWidth: 1,
                    borderColor: COLORS.BORDER,
                  }}
                >
                  <View
                    style={{
                      paddingHorizontal: 6,
                      paddingVertical: 2,
                      borderRadius: 3,
                      backgroundColor: COLORS.GREEN,
                      marginRight: 8,
                    }}
                  >
                    <Text style={{ fontSize: 7, color: "#fff", fontWeight: "bold" }}>
                      PASS
                    </Text>
                  </View>
                  <Text style={{ fontSize: 8, color: COLORS.TEXT_SEC }}>
                    {agentDisplayLabel(agentKey)}
                    {agentDisp == null ? " — pending" : ""}
                  </Text>
                </View>
              );
            }

            // Rejected agent — full three-part narrative block
            const rejectLabel = sanitizeText(insight?.reject_label ?? "REJECTED");
            const rootCauseText = sanitizeText(insight?.root_cause ?? "");
            const rationaleText = sanitizeText(insight?.disposition_rationale ?? "");
            const consequenceText = sanitizeText(insight?.consequence ?? "");
            const actions = insight?.corrective_actions ?? [];

            return (
              <View
                key={agentKey}
                style={{
                  marginBottom: 12,
                  backgroundColor: COLORS.PANEL,
                  borderRadius: 6,
                  borderWidth: 1,
                  borderColor: COLORS.BORDER,
                  padding: 12,
                }}
              >
                {/* Header row: reject badge + agent label */}
                <View
                  style={{
                    flexDirection: "row",
                    alignItems: "center",
                    marginBottom: 10,
                  }}
                >
                  <View
                    style={{
                      paddingHorizontal: 6,
                      paddingVertical: 2,
                      borderRadius: 3,
                      backgroundColor: COLORS.RED,
                      marginRight: 8,
                    }}
                  >
                    <Text style={{ fontSize: 7, color: "#fff", fontWeight: "bold" }}>
                      {rejectLabel}
                    </Text>
                  </View>
                  <Text
                    style={{
                      fontSize: 9,
                      color: COLORS.TEXT_SEC,
                      textTransform: "uppercase",
                      letterSpacing: 1,
                    }}
                  >
                    {agentDisplayLabel(agentKey)}
                  </Text>
                </View>

                {/* Part 1 — What happened */}
                {rootCauseText !== "" && (
                  <View style={{ marginBottom: 8 }}>
                    <Text
                      style={{
                        fontSize: 7,
                        color: COLORS.TEXT_SEC,
                        textTransform: "uppercase",
                        letterSpacing: 1,
                        marginBottom: 3,
                      }}
                    >
                      What happened
                    </Text>
                    <Text style={{ fontSize: 9, color: COLORS.TEXT_PRI, lineHeight: 1.5 }}>
                      {rootCauseText}
                    </Text>
                  </View>
                )}

                {/* Part 2 — In the analysis */}
                {rationaleText !== "" && (
                  <View style={{ marginBottom: 8 }}>
                    <Text
                      style={{
                        fontSize: 7,
                        color: COLORS.TEXT_SEC,
                        textTransform: "uppercase",
                        letterSpacing: 1,
                        marginBottom: 3,
                      }}
                    >
                      In the analysis
                    </Text>
                    <Text style={{ fontSize: 9, color: COLORS.TEXT_PRI, lineHeight: 1.5 }}>
                      {rationaleText}
                    </Text>
                  </View>
                )}

                {/* Part 3 — Potential weld risk */}
                {consequenceText !== "" && (
                  <View style={{ marginBottom: 8 }}>
                    <Text
                      style={{
                        fontSize: 7,
                        color: COLORS.TEXT_SEC,
                        textTransform: "uppercase",
                        letterSpacing: 1,
                        marginBottom: 3,
                      }}
                    >
                      Potential weld risk
                    </Text>
                    <Text style={{ fontSize: 9, color: COLORS.TEXT_SEC, lineHeight: 1.5 }}>
                      {consequenceText}
                    </Text>
                  </View>
                )}

                {/* Corrective actions */}
                {actions.length > 0 && (
                  <View>
                    <Text
                      style={{
                        fontSize: 7,
                        color: COLORS.TEXT_SEC,
                        textTransform: "uppercase",
                        letterSpacing: 1,
                        marginBottom: 4,
                      }}
                    >
                      Corrective Actions
                    </Text>
                    {actions.map((action, i) => (
                      <View
                        key={`action-${agentKey}-${i}`}
                        style={{ flexDirection: "row", marginBottom: 4 }}
                      >
                        <Text
                          style={{
                            fontSize: 9,
                            color: COLORS.ACCENT,
                            fontWeight: "bold",
                            minWidth: 16,
                            marginRight: 4,
                          }}
                        >
                          {i + 1}.
                        </Text>
                        <Text
                          style={{
                            fontSize: 9,
                            color: COLORS.TEXT_PRI,
                            flex: 1,
                            lineHeight: 1.4,
                          }}
                        >
                          {sanitizeText(action)}
                        </Text>
                      </View>
                    ))}
                  </View>
                )}
              </View>
            );
          })}
        </View>

        {/* FOOTER */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>WarpSense Quality Intelligence</Text>
          <Text style={styles.footerText}>CONFIDENTIAL — Internal use only</Text>
        </View>
      </Page>
    </Document>
  );
}
