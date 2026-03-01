/**
 * PDF layout component for welder session report.
 *
 * Uses @react-pdf/renderer — PDF-native components, no DOM or canvas capture.
 * Renders on server in Next.js API route.
 * Layout aligns with reference design: Letter size, WarpSense branding, compliance badges.
 */

import {
  Document,
  Page,
  View,
  Text,
  StyleSheet,
  Image,
} from "@react-pdf/renderer";
import type { ReportSummary } from "@/types/report-summary";

/** Reference palette from design spec. */
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

function formatTime(ms: number): string {
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
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
    height: 88,
    backgroundColor: COLORS.PANEL,
    marginHorizontal: -40,
    marginTop: -40,
    paddingHorizontal: 40,
    paddingTop: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.BORDER,
  },
  topBarLeft: { flex: 1 },
  logo: { fontSize: 14, color: COLORS.ACCENT, fontWeight: "bold", marginBottom: 2 },
  tagline: { fontSize: 8, color: COLORS.TEXT_SEC, marginBottom: 6 },
  welderName: {
    fontSize: 18,
    color: COLORS.TEXT_PRI,
    fontWeight: "bold",
    marginBottom: 4,
  },
  metaLine: { fontSize: 9, color: COLORS.TEXT_SEC },
  scoreCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    borderWidth: 3,
    borderColor: COLORS.ACCENT,
    alignItems: "center",
    justifyContent: "center",
  },
  scoreText: { fontSize: 22, color: COLORS.ACCENT, fontWeight: "bold" },
  scoreDenom: { fontSize: 8, color: COLORS.TEXT_SEC },
  sectionTitle: {
    fontSize: 10,
    color: COLORS.TEXT_SEC,
    textTransform: "uppercase",
    letterSpacing: 2,
    marginBottom: 8,
  },
  panel: {
    marginTop: 16,
    padding: 14,
    backgroundColor: COLORS.PANEL,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: COLORS.BORDER,
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
    minWidth: 36,
    alignItems: "center",
    justifyContent: "center",
  },
  badgePass: { backgroundColor: COLORS.GREEN },
  badgeFail: { backgroundColor: COLORS.RED },
  badgeText: { fontSize: 8, color: "#fff", fontWeight: "bold" },
  complianceRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 6,
  },
  complianceLabel: { fontSize: 9, color: COLORS.TEXT_SEC },
  complianceDetail: { fontSize: 9, color: COLORS.TEXT_PRI, flex: 1, marginHorizontal: 8 },
  feedbackItem: { flexDirection: "row", marginBottom: 8, paddingLeft: 4 },
  footer: {
    position: "absolute",
    bottom: 30,
    left: 40,
    right: 40,
    borderTopWidth: 1,
    borderTopColor: COLORS.BORDER,
    paddingTop: 12,
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
  chartDataUrl?: string | null;
  narrative?: string | null;
  certifications?: Array<{
    name: string;
    status: string;
    qualifying_sessions: number;
    sessions_required: number;
  }> | null;
  reportSummary?: ReportSummary | null;
  /** Optional session date for top-bar meta (e.g. "2/27/2026"). */
  sessionDate?: string | null;
  /** Optional duration string (e.g. "4 min 12 sec") for top-bar meta. */
  duration?: string | null;
  /** Optional station placeholder (e.g. "Station 4") for top-bar meta. */
  station?: string | null;
}

function isPngDataUrl(v: unknown): v is string {
  return typeof v === "string" && v.startsWith("data:image/png");
}

export function toWelderName(v: unknown): string {
  if (typeof v === "string" && v.trim().length > 0) return v.trim();
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return "Unknown";
}

function severityToColor(severity: string): string {
  const s = String(severity).toLowerCase();
  if (s === "critical") return COLORS.RED;
  if (s === "warning") return COLORS.AMBER;
  if (s === "info") return COLORS.GREEN;
  return COLORS.ACCENT;
}

export function WelderReportPDF({
  welder,
  score,
  feedback,
  chartDataUrl,
  narrative,
  certifications,
  reportSummary,
  sessionDate,
  duration,
  station,
}: WelderReportPDFProps) {
  const rawItems = feedback?.feedback_items ?? [];
  const validItems = rawItems.filter(
    (
      item
    ): item is {
      message: string;
      severity: string;
      suggestion?: string | null;
    } =>
      item != null &&
      typeof item === "object" &&
      typeof (item as { message?: unknown }).message === "string" &&
      typeof (item as { severity?: unknown }).severity === "string"
  );
  const top3 = validItems.slice(0, 3);
  const welderName = sanitizeText(toWelderName(welder?.name ?? "Unknown"));
  const totalScore = score?.total ?? 0;
  const summary = sanitizeText(feedback?.summary ?? "");
  const chartPng = isPngDataUrl(chartDataUrl) ? chartDataUrl : null;

  const metaParts: string[] = [];
  if (sessionDate) metaParts.push(sessionDate);
  if (station) metaParts.push(station);
  if (duration) metaParts.push(duration);
  const metaLine =
    metaParts.length > 0
      ? `Session Report · ${metaParts.join(" · ")}`
      : "Session Report · —";

  const coachText =
    narrative && narrative.trim()
      ? sanitizeText(narrative)
      : summary || "—";

  return (
    <Document>
      <Page size="LETTER" style={styles.page}>
        {/* TopBar: branding, operator, meta, score circle */}
        <View style={styles.topBar}>
          <View style={styles.topBarLeft}>
            <Text style={styles.logo}>WARPSENSE</Text>
            <Text style={styles.tagline}>Quality Intelligence Platform</Text>
            <Text style={styles.welderName}>{welderName}</Text>
            <Text style={styles.metaLine}>{metaLine}</Text>
          </View>
          <View style={styles.scoreCircle}>
            <View style={{ alignItems: "center" }}>
              <Text style={styles.scoreText}>{totalScore}</Text>
              <Text style={styles.scoreDenom}>/ 100</Text>
            </View>
          </View>
        </View>

        {/* Compliance: PASS/FAIL badges */}
        {reportSummary && (
          <View style={styles.panel}>
            <Text style={styles.sectionTitle}>Compliance</Text>
            <View style={styles.complianceRow}>
              <Text style={styles.complianceLabel}>Heat Input</Text>
              <Text style={styles.complianceDetail}>
                {reportSummary.heat_input_mean_kj_per_mm != null
                  ? `${reportSummary.heat_input_mean_kj_per_mm.toFixed(2)} kJ/mm (WPS ${reportSummary.heat_input_wps_min}–${reportSummary.heat_input_wps_max})`
                  : "—"}
              </Text>
              <View
                style={[
                  styles.badge,
                  reportSummary.heat_input_compliant
                    ? styles.badgePass
                    : styles.badgeFail,
                ]}
              >
                <Text style={styles.badgeText}>
                  {reportSummary.heat_input_compliant ? "PASS" : "FAIL"}
                </Text>
              </View>
            </View>
            <View style={styles.complianceRow}>
              <Text style={styles.complianceLabel}>Torch Angle</Text>
              <Text style={styles.complianceDetail}>
                {reportSummary.travel_angle_excursion_count === 0
                  ? `Within ±${reportSummary.travel_angle_threshold_deg}°`
                  : `${reportSummary.travel_angle_excursion_count} excursion(s)`}
              </Text>
              <View
                style={[
                  styles.badge,
                  reportSummary.travel_angle_excursion_count === 0
                    ? styles.badgePass
                    : styles.badgeFail,
                ]}
              >
                <Text style={styles.badgeText}>
                  {reportSummary.travel_angle_excursion_count === 0
                    ? "PASS"
                    : "FAIL"}
                </Text>
              </View>
            </View>
            <View style={styles.complianceRow}>
              <Text style={styles.complianceLabel}>Arc Termination</Text>
              <Text style={styles.complianceDetail}>
                {reportSummary.total_arc_terminations > 0
                  ? `${reportSummary.crater_fill_rate_pct.toFixed(0)}% crater fill`
                  : "No terminations"}
              </Text>
              <View
                style={[
                  styles.badge,
                  reportSummary.total_arc_terminations === 0 ||
                  reportSummary.crater_fill_rate_pct >= 100
                    ? styles.badgePass
                    : styles.badgeFail,
                ]}
              >
                <Text style={styles.badgeText}>
                  {reportSummary.total_arc_terminations === 0 ||
                  reportSummary.crater_fill_rate_pct >= 100
                    ? "PASS"
                    : "FAIL"}
                </Text>
              </View>
            </View>
            {reportSummary.excursions.length > 0 && (
              <View style={{ marginTop: 8 }}>
                <Text
                  style={{
                    fontSize: 8,
                    color: COLORS.TEXT_SEC,
                    marginBottom: 4,
                  }}
                >
                  Excursion Log
                </Text>
                {[...reportSummary.excursions]
                  .sort((a, b) => a.timestamp_ms - b.timestamp_ms)
                  .slice(0, 10)
                  .map((e, i) => (
                    <View
                      key={`${e.timestamp_ms}-${e.defect_type}-${i}`}
                      style={{
                        flexDirection: "row",
                        gap: 8,
                        paddingVertical: 2,
                        borderBottomWidth: 0.5,
                        borderBottomColor: COLORS.BORDER,
                      }}
                    >
                      <Text
                        style={{
                          color: COLORS.TEXT_SEC,
                          minWidth: 36,
                          fontSize: 8,
                        }}
                      >
                        {formatTime(e.timestamp_ms)}
                      </Text>
                      <Text
                        style={{ color: COLORS.TEXT_PRI, fontSize: 8 }}
                      >
                        {e.defect_type}
                      </Text>
                      {e.parameter_value != null && (
                        <Text
                          style={{ color: COLORS.TEXT_SEC, fontSize: 8 }}
                        >
                          {e.parameter_value}
                        </Text>
                      )}
                      {e.notes && (
                        <Text
                          style={{
                            color: COLORS.TEXT_SEC,
                            flex: 1,
                            fontSize: 8,
                          }}
                        >
                          {sanitizeText(
                            String(e.notes).slice(0, 60) +
                              (String(e.notes).length > 60 ? "…" : "")
                          )}
                        </Text>
                      )}
                    </View>
                  ))}
              </View>
            )}
          </View>
        )}

        {/* Coach Feedback: narrative when present, else feedback.summary */}
        <View style={[styles.panel, { marginTop: 16 }]}>
          <Text style={styles.sectionTitle}>Coach Feedback</Text>
          <Text
            style={{
              fontSize: 10,
              color: COLORS.TEXT_PRI,
              lineHeight: 1.6,
            }}
          >
            {coachText}
          </Text>
        </View>

        {/* Score Trend */}
        {chartPng && (
          <View style={{ marginTop: 16, marginBottom: 16 }}>
            <Text style={styles.sectionTitle}>Score Trend (Last 5 Sessions)</Text>
            <Image src={chartPng} style={{ height: 120 }} />
          </View>
        )}

        {/* Key Areas: severity→color mapping */}
        <View style={{ marginTop: 16 }}>
          <Text style={styles.sectionTitle}>Key Areas for Improvement</Text>
          {top3.length > 0 ? (
            top3.map((item, i) => {
              const dotColor = severityToColor(item.severity);
              return (
                <View key={`fb-${i}`} style={styles.feedbackItem}>
                  <View
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: 4,
                      backgroundColor: dotColor,
                      marginRight: 10,
                      marginTop: 4,
                    }}
                  />
                  <View style={{ flex: 1 }}>
                    <Text
                      style={{
                        fontSize: 10,
                        color: COLORS.TEXT_PRI,
                        fontWeight: "bold",
                      }}
                    >
                      {sanitizeText(item.message)}
                    </Text>
                    {item.suggestion && (
                      <Text
                        style={{
                          fontSize: 9,
                          color: COLORS.TEXT_SEC,
                          marginTop: 2,
                        }}
                      >
                        {sanitizeText(item.suggestion)}
                      </Text>
                    )}
                  </View>
                </View>
              );
            })
          ) : (
            <Text style={{ fontSize: 9, color: COLORS.TEXT_SEC }}>
              No key areas identified.
            </Text>
          )}
        </View>

        {/* Certifications */}
        {certifications && certifications.length > 0 && (
          <View style={[styles.panel, { marginTop: 16 }]}>
            <Text style={styles.sectionTitle}>Certification Readiness</Text>
            {certifications.map((c, i) => (
              <View
                key={`${sanitizeText(c.name)}-${i}`}
                style={{
                  flexDirection: "row",
                  justifyContent: "space-between",
                  paddingVertical: 3,
                  borderBottomWidth: 0.5,
                  borderBottomColor: COLORS.BORDER,
                }}
              >
                <Text style={{ fontSize: 9, color: COLORS.TEXT_PRI }}>
                  {sanitizeText(c.name)}
                </Text>
                <Text style={{ fontSize: 9, color: COLORS.TEXT_SEC }}>
                  {c.qualifying_sessions}/{c.sessions_required} ·{" "}
                  {sanitizeText(c.status)}
                </Text>
              </View>
            ))}
          </View>
        )}

        {/* Footer */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>
            WarpSense Quality Intelligence
          </Text>
          <Text style={styles.footerText}>
            CONFIDENTIAL — Internal use only
          </Text>
        </View>
      </Page>
    </Document>
  );
}
