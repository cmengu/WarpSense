/**
 * PDF layout component for welder session report.
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
  Image,
} from "@react-pdf/renderer";
import type { ReportSummary } from "@/types/report-summary";

/** Sanitize text for PDF rendering. Strips control chars, zero-width, RTL-override. */
function sanitizeText(str: string): string {
  if (typeof str !== "string") return "";
  return str
    .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g, "")
    .replace(/[\u200b-\u200d\u2060\ufeff]/g, "") // zero-width chars
    .replace(/[\u202a-\u202e\u2066-\u2069]/g, "") // RTL override
    .replace(/</g, "‹")
    .replace(/>/g, "›");
}

const styles = StyleSheet.create({
  page: {
    backgroundColor: "#0a0a0a",
    padding: 40,
    fontFamily: "Helvetica",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 24,
  },
  scoreCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    border: "3px solid #3b82f6",
    alignItems: "center",
    justifyContent: "center",
  },
  scoreText: { fontSize: 28, color: "#3b82f6", fontWeight: "bold" },
  sectionTitle: {
    fontSize: 10,
    color: "#6b7280",
    textTransform: "uppercase",
    letterSpacing: 2,
    marginBottom: 8,
  },
  feedbackItem: { flexDirection: "row", marginBottom: 6, paddingLeft: 12 },
  bullet: { color: "#f59e0b", marginRight: 8 },
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
  /** Optional AI Coach narrative; renders section between score and feedback if present. */
  narrative?: string | null;
  /** Optional certification readiness; renders table after feedback if present. */
  certifications?: Array<{
    name: string;
    status: string;
    qualifying_sessions: number;
    sessions_required: number;
  }> | null;
  /** Optional compliance summary; renders section before feedback if present. */
  reportSummary?: ReportSummary | null;
}

function isPngDataUrl(v: unknown): v is string {
  return typeof v === "string" && v.startsWith("data:image/png");
}

/** Coerce welder name to string; always returns string. Whitespace-only → "Unknown". Matches API route behavior. */
export function toWelderName(v: unknown): string {
  if (typeof v === "string" && v.trim().length > 0) return v.trim();
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return "Unknown";
}

function formatTime(ms: number): string {
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

export function WelderReportPDF({
  welder,
  score,
  feedback,
  chartDataUrl,
  narrative,
  certifications,
  reportSummary,
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

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <View style={styles.header}>
          <View>
            <Text style={{ fontSize: 20, color: "#f9fafb", fontWeight: "bold" }}>
              {welderName}
            </Text>
            <Text style={{ fontSize: 10, color: "#6b7280", marginTop: 4 }}>
              Session Report · {new Date().toLocaleDateString()}
            </Text>
          </View>
          <View style={styles.scoreCircle}>
            <Text style={styles.scoreText}>{totalScore}</Text>
          </View>
        </View>

        {reportSummary && (
          <View
            style={{
              marginTop: 16,
              padding: 12,
              backgroundColor: "#1a1a2e",
              borderRadius: 6,
            }}
          >
            <Text
              style={{
                fontSize: 8,
                color: "#737373",
                textTransform: "uppercase",
                letterSpacing: 1,
                marginBottom: 6,
              }}
            >
              Compliance
            </Text>
            <View style={{ gap: 4 }}>
              <Text style={{ fontSize: 9, color: "#d4d4d4" }}>
                Heat Input:{" "}
                {reportSummary.heat_input_mean_kj_per_mm != null
                  ? `${reportSummary.heat_input_mean_kj_per_mm.toFixed(2)} kJ/mm (WPS ${reportSummary.heat_input_wps_min}–${reportSummary.heat_input_wps_max})`
                  : "—"}{" "}
                {reportSummary.heat_input_compliant ? "✓ PASS" : "✗ FAIL"}
              </Text>
              <Text style={{ fontSize: 9, color: "#d4d4d4" }}>
                Torch Angle:{" "}
                {reportSummary.travel_angle_excursion_count === 0
                  ? `Within ±${reportSummary.travel_angle_threshold_deg}° ✓ PASS`
                  : `${reportSummary.travel_angle_excursion_count} excursion(s) ✗ FAIL`}
              </Text>
              <Text style={{ fontSize: 9, color: "#d4d4d4" }}>
                Arc Termination:{" "}
                {reportSummary.total_arc_terminations > 0
                  ? `${reportSummary.crater_fill_rate_pct.toFixed(0)}% crater fill (${reportSummary.total_arc_terminations - reportSummary.no_crater_fill_count}/${reportSummary.total_arc_terminations})`
                  : "No terminations"}{" "}
                {reportSummary.total_arc_terminations === 0 ||
                reportSummary.crater_fill_rate_pct >= 100
                  ? "✓ PASS"
                  : "✗ FAIL"}
              </Text>
            </View>
            {reportSummary.excursions.length > 0 && (
              <View style={{ marginTop: 8 }}>
                <Text
                  style={{
                    fontSize: 8,
                    color: "#737373",
                    marginBottom: 4,
                  }}
                >
                  Excursion Log
                </Text>
                {reportSummary.excursions
                  .slice(0, 10)
                  .sort((a, b) => a.timestamp_ms - b.timestamp_ms)
                  .map((e, i) => (
                    <View
                      key={i}
                      style={{
                        flexDirection: "row",
                        gap: 8,
                        paddingVertical: 2,
                        borderBottomWidth: 0.5,
                        borderBottomColor: "#262626",
                      }}
                    >
                      <Text style={{ color: "#9ca3af", minWidth: 36 }}>
                        {formatTime(e.timestamp_ms)}
                      </Text>
                      <Text style={{ color: "#d4d4d4" }}>{e.defect_type}</Text>
                      {e.parameter_value != null && (
                        <Text style={{ color: "#9ca3af" }}>
                          {e.parameter_value}
                        </Text>
                      )}
                      {e.notes && (
                        <Text style={{ color: "#6b7280", flex: 1 }}>
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

        {narrative && (
          <View
            style={{
              marginTop: 16,
              padding: 12,
              backgroundColor: "#1a1a2e",
              borderRadius: 6,
            }}
          >
            <Text
              style={{
                fontSize: 8,
                color: "#737373",
                textTransform: "uppercase",
                letterSpacing: 1,
                marginBottom: 6,
              }}
            >
              AI Coach Report
            </Text>
            <Text
              style={{ fontSize: 9, color: "#d4d4d4", lineHeight: 1.6 }}
            >
              {sanitizeText(narrative)}
            </Text>
          </View>
        )}

        <Text style={styles.sectionTitle}>Coach Feedback</Text>
        <Text
          style={{
            fontSize: 11,
            color: "#d1d5db",
            lineHeight: 1.6,
            marginBottom: 20,
          }}
        >
          {summary || "—"}
        </Text>

        {chartPng && (
          <View style={{ marginBottom: 20 }}>
            <Text style={styles.sectionTitle}>
              Score Trend (Last 5 Sessions)
            </Text>
            <Image src={chartPng} style={{ height: 120 }} />
          </View>
        )}

        <Text style={styles.sectionTitle}>Key Areas</Text>
        {top3.map((item, i) => (
          <View key={`fb-${i}`} style={styles.feedbackItem}>
            <Text style={styles.bullet}>
              {item.severity === "warning" || item.severity === "critical"
                ? "⚠"
                : "•"}
            </Text>
            <View>
              <Text style={{ fontSize: 10, color: "#f9fafb" }}>
                {sanitizeText(item.message)}
              </Text>
              {item.suggestion && (
                <Text style={{ fontSize: 9, color: "#6b7280", marginTop: 2 }}>
                  → {sanitizeText(item.suggestion)}
                </Text>
              )}
            </View>
          </View>
        ))}

        {certifications && certifications.length > 0 && (
          <View style={{ marginTop: 16 }}>
            <Text
              style={{
                fontSize: 8,
                color: "#737373",
                textTransform: "uppercase",
                letterSpacing: 1,
                marginBottom: 6,
              }}
            >
              Certification Readiness
            </Text>
            {certifications.map((c, i) => (
              <View
                key={i}
                style={{
                  flexDirection: "row",
                  justifyContent: "space-between",
                  paddingVertical: 3,
                  borderBottomWidth: 0.5,
                  borderBottomColor: "#262626",
                }}
              >
                <Text style={{ fontSize: 9, color: "#d4d4d4" }}>
                  {sanitizeText(c.name)}
                </Text>
                <Text style={{ fontSize: 9, color: "#737373" }}>
                  {c.qualifying_sessions}/{c.sessions_required} ·{" "}
                  {sanitizeText(c.status)}
                </Text>
              </View>
            ))}
          </View>
        )}

        <View
          style={{
            position: "absolute",
            bottom: 30,
            left: 40,
            right: 40,
            borderTop: "1px solid #1f2937",
            paddingTop: 12,
            flexDirection: "row",
            justifyContent: "space-between",
          }}
        >
          <Text style={{ fontSize: 8, color: "#374151" }}>
            WarpSense Quality Intelligence
          </Text>
          <Text style={{ fontSize: 8, color: "#374151" }}>CONFIDENTIAL</Text>
        </View>
      </Page>
    </Document>
  );
}
