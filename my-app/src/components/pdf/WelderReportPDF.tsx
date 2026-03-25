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
  welder: { name: string };
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
  welder,
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
  const welderName = sanitizeText(toWelderName(welder?.name ?? "Unknown"));
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

  const rootCause = sanitizeText(feedback?.summary ?? "");
  const rawRationale = narrative ?? "";
  const rationale = sanitizeText(
    rawRationale.slice(0, 400) + (rawRationale.length > 400 ? "…" : "")
  );
  const corrective = (feedback?.feedback_items ?? []).slice(0, 5);

  /**
   * Build insight map keyed by agent_name (PascalCase).
   * AGENT_ORDER matches the canonical values from backend/agent/specialists.py:
   *   for agent_name in ["ThermalAgent", "GeometryAgent", "ProcessStabilityAgent"]
   */
  const AGENT_ORDER = ["ThermalAgent", "GeometryAgent", "ProcessStabilityAgent"];
  const insightMap: Record<string, { disposition?: string; root_cause?: string }> = {};
  for (const row of agentInsights ?? []) {
    insightMap[row.agent_name] = {
      disposition: row.disposition,
      root_cause: row.root_cause,
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
            <Text style={styles.welderName}>{welderName}</Text>
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

        {/* HERO: REWORK COST */}
        <View
          style={{
            marginTop: 24,
            paddingVertical: 28,
            alignItems: "center",
            backgroundColor: COLORS.PANEL,
            borderRadius: 6,
            borderWidth: 2,
            borderColor: costColor,
          }}
        >
          <Text
            style={{
              fontSize: 9,
              color: COLORS.TEXT_SEC,
              textTransform: "uppercase",
              letterSpacing: 2,
              marginBottom: 10,
            }}
          >
            Estimated Rework Cost
          </Text>
          <Text
            style={{
              fontSize: 64,
              fontWeight: "bold",
              color: costColor,
              fontFamily: "Helvetica-Bold",
            }}
          >
            {formatCost(cost)}
          </Text>
        </View>

        {/* REJECTION SUMMARY */}
        <View style={styles.panel}>
          <Text style={styles.sectionTitle}>Rejection Summary</Text>
          {rootCause !== "" && (
            <Text
              style={{
                fontSize: 12,
                color: COLORS.TEXT_PRI,
                fontWeight: "bold",
                marginBottom: rationale !== "" ? 8 : 0,
              }}
            >
              {rootCause}
            </Text>
          )}
          {rationale !== "" && (
            <Text style={{ fontSize: 9, color: COLORS.TEXT_SEC, lineHeight: 1.5 }}>
              {rationale}
            </Text>
          )}
        </View>

        {/* 3 AGENT FINDINGS */}
        <View style={{ marginTop: 16 }}>
          <Text style={styles.sectionTitle}>Agent Findings</Text>
          <View style={{ flexDirection: "row" }}>
            {AGENT_ORDER.map((agentKey, idx) => {
              const insight = insightMap[agentKey];
              const agentDisp = insight?.disposition;
              const rawRoot = insight?.root_cause ?? "";
              const agentRoot =
                rawRoot !== ""
                  ? sanitizeText(
                      rawRoot.slice(0, 120) + (rawRoot.length > 120 ? "…" : "")
                    )
                  : "—";
              const agentDispColor = dispositionColor(agentDisp);
              return (
                <View
                  key={agentKey}
                  style={{
                    flex: 1,
                    backgroundColor: COLORS.PANEL,
                    borderRadius: 6,
                    borderWidth: 1,
                    borderColor: COLORS.BORDER,
                    padding: 10,
                    marginRight: idx < 2 ? 8 : 0,
                  }}
                >
                  <Text
                    style={{
                      fontSize: 8,
                      color: COLORS.TEXT_SEC,
                      textTransform: "uppercase",
                      letterSpacing: 1,
                      marginBottom: 6,
                    }}
                  >
                    {agentDisplayLabel(agentKey)}
                  </Text>
                  {agentDisp != null && (
                    <View
                      style={{
                        paddingHorizontal: 6,
                        paddingVertical: 2,
                        borderRadius: 3,
                        backgroundColor: agentDispColor,
                        alignSelf: "flex-start",
                        marginBottom: 6,
                      }}
                    >
                      <Text
                        style={{ fontSize: 7, color: "#fff", fontWeight: "bold" }}
                      >
                        {dispositionLabel(agentDisp)}
                      </Text>
                    </View>
                  )}
                  <Text
                    style={{ fontSize: 8, color: COLORS.TEXT_PRI, lineHeight: 1.4 }}
                  >
                    {agentRoot}
                  </Text>
                </View>
              );
            })}
          </View>
        </View>

        {/* CORRECTIVE ACTIONS */}
        {corrective.length > 0 && (
          <View style={styles.panel}>
            <Text style={styles.sectionTitle}>Corrective Actions</Text>
            {corrective.map((item, i) => (
              <View
                key={`ca-${i}`}
                style={{ flexDirection: "row", marginBottom: 6 }}
              >
                <Text
                  style={{
                    fontSize: 9,
                    color: COLORS.ACCENT,
                    fontWeight: "bold",
                    minWidth: 18,
                    marginRight: 6,
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
                  {sanitizeText(item.message)}
                </Text>
              </View>
            ))}
          </View>
        )}

        {/* FOOTER */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>WarpSense Quality Intelligence</Text>
          <Text style={styles.footerText}>CONFIDENTIAL — Internal use only</Text>
        </View>
      </Page>
    </Document>
  );
}
