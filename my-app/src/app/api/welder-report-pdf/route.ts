/**
 * POST /api/welder-report-pdf
 *
 * Accepts welder, score, feedback, optional chartDataUrl.
 * Returns application/pdf with Content-Disposition attachment.
 * Body limit 5MB; chartDataUrl limit 2MB; only data:image/png accepted.
 */

import { NextResponse } from "next/server";
import { renderToBuffer } from "@react-pdf/renderer";
import React from "react";
import { logError, logWarn } from "@/lib/logger";
import { WelderReportPDF, type WelderReportPDFProps } from "@/components/pdf/WelderReportPDF";
import type { SessionScore } from "@/lib/api";
import type { ReportSummary } from "@/types/report-summary";

/** WelderReportPDF returns <Document>; renderToBuffer expects Document root. Type assertion for TS. */
const toPdfDoc = (el: React.ReactElement) =>
  el as Parameters<typeof renderToBuffer>[0];

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

interface PDFRequestBody {
  welder?: { name?: unknown };
  score?: SessionScore | { total: number; rules?: unknown[] };
  feedback?: { summary?: string; feedback_items?: unknown[] };
  chartDataUrl?: unknown;
  /** Optional AI Coach narrative; max 2000 chars. PDF renders without if absent. */
  narrative?: string | null;
  /** Optional report summary; PDF renders compliance section if present. Omit and log warning if absent. */
  reportSummary?: unknown;
  /** Optional certification readiness; PDF renders table section if present. */
  certifications?: Array<{
    name: string;
    status: string;
    qualifying_sessions: number;
    sessions_required: number;
  }> | null;
  /** Optional session date for top-bar meta (e.g. "2/27/2026"). */
  sessionDate?: string | null;
  /** Optional duration string (e.g. "4 min 12 sec") for top-bar meta. */
  duration?: string | null;
  /** Optional station placeholder (e.g. "Station 4") for top-bar meta. */
  station?: string | null;
  /** Estimated rework cost in USD — drives the hero block in the PDF. */
  rework_cost_usd?: number | null;
  /** Weld disposition — PASS | CONDITIONAL | REWORK_REQUIRED. */
  disposition?: string | null;
  /** Per-agent parsed insights from llm_raw_response. */
  agentInsights?: Array<{
    agent_name: string;
    disposition?: string;
    root_cause?: string;
    corrective_actions?: string[];
  }> | null;
}

const MAX_FILENAME_LENGTH = 64;
const MAX_CHART_DATA_URL_LENGTH = 2 * 1024 * 1024; // 2MB
const MAX_BODY_SIZE_BYTES = 5 * 1024 * 1024; // 5MB total

function sanitizeFilename(name: string): string {
  const sanitized = String(name).replace(/[^a-zA-Z0-9_-]/g, "-");
  return sanitized.slice(0, MAX_FILENAME_LENGTH) || "welder";
}

function toWelderName(v: unknown): string {
  if (typeof v === "string" && v.trim().length > 0) return v.trim();
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return "Unknown";
}

function isValidFeedbackItem(
  item: unknown
): item is {
  message: string;
  severity: string;
  suggestion?: string | null;
} {
  if (!item || typeof item !== "object") return false;
  const o = item as Record<string, unknown>;
  return (
    typeof o.message === "string" &&
    o.message.length > 0 &&
    typeof o.severity === "string"
  );
}

export async function POST(request: Request) {
  const contentLength = request.headers.get("content-length");
  const transferEncoding = request.headers.get("transfer-encoding");
  const isChunked = transferEncoding?.toLowerCase().includes("chunked");

  if (isChunked && !contentLength) {
    return NextResponse.json(
      {
        error:
          "Chunked transfer encoding not supported. Send Content-Length header for body size verification (max 5MB).",
      },
      { status: 411 }
    );
  }

  if (contentLength) {
    const size = parseInt(contentLength, 10);
    if (Number.isNaN(size) || size < 0) {
      return NextResponse.json(
        { error: "Invalid Content-Length header" },
        { status: 400 }
      );
    }
    if (size > MAX_BODY_SIZE_BYTES) {
      return NextResponse.json(
        {
          error: `Request body exceeds max size (${MAX_BODY_SIZE_BYTES} bytes)`,
        },
        { status: 413 }
      );
    }
  }

  let body: PDFRequestBody;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "Invalid JSON body" },
      { status: 400 }
    );
  }

  if (!body.welder || typeof body.welder !== "object") {
    return NextResponse.json(
      { error: "Missing or invalid welder" },
      { status: 400 }
    );
  }
  const welderName = toWelderName(body.welder.name);

  if (!body.score || typeof body.score !== "object") {
    return NextResponse.json(
      { error: "Missing or invalid score" },
      { status: 400 }
    );
  }
  const total = body.score.total;
  if (typeof total !== "number" || !Number.isFinite(total)) {
    return NextResponse.json(
      { error: "score.total must be a number" },
      { status: 400 }
    );
  }
  if (!body.feedback || typeof body.feedback !== "object") {
    return NextResponse.json(
      { error: "Missing or invalid feedback" },
      { status: 400 }
    );
  }

  const rawItems = body.feedback.feedback_items ?? [];
  if (!Array.isArray(rawItems)) {
    return NextResponse.json(
      { error: "feedback.feedback_items must be an array" },
      { status: 400 }
    );
  }
  const feedback_items = rawItems.filter(isValidFeedbackItem);
  if (feedback_items.length === 0 && rawItems.length > 0) {
    return NextResponse.json(
      {
        error:
          "Each feedback item must have non-empty message and severity (string)",
      },
      { status: 400 }
    );
  }

  let chartDataUrl: string | null = null;
  if (body.chartDataUrl != null && typeof body.chartDataUrl === "string") {
    if (!body.chartDataUrl.startsWith("data:image/png")) {
      chartDataUrl = null;
    } else if (body.chartDataUrl.length > MAX_CHART_DATA_URL_LENGTH) {
      return NextResponse.json(
        {
          error: `chartDataUrl exceeds max length (${MAX_CHART_DATA_URL_LENGTH} bytes)`,
        },
        { status: 400 }
      );
    } else {
      chartDataUrl = body.chartDataUrl;
    }
  }

  /** Optional AI Coach narrative; validated max 2000 chars. Omit if invalid. */
  let narrative: string | null = null;
  if (
    body.narrative != null &&
    typeof body.narrative === "string" &&
    body.narrative.length <= 2000
  ) {
    narrative = body.narrative;
  } else if (body.narrative != null && typeof body.narrative === "string") {
    return NextResponse.json(
      { error: "narrative exceeds max length (2000 chars)" },
      { status: 400 }
    );
  }

  /** Optional reportSummary; validate and pass to PDF. Log warning if absent. */
  let reportSummary: ReportSummary | null = null;
  if (body.reportSummary != null) {
    const rs = body.reportSummary as Record<string, unknown>;
    if (
      rs &&
      typeof rs === "object" &&
      typeof rs.session_id === "string" &&
      Array.isArray(rs.excursions)
    ) {
      reportSummary = body.reportSummary as ReportSummary;
    }
  } else {
    logWarn(
      "welder-report-pdf",
      "reportSummary absent in PDF request — fetch may have failed"
    );
  }

  /** Optional certifications; validate structure if provided. */
  let certifications: PDFRequestBody["certifications"] = null;
  if (body.certifications != null) {
    if (!Array.isArray(body.certifications)) {
      return NextResponse.json(
        { error: "certifications must be an array" },
        { status: 400 }
      );
    }
    const valid: Array<{
      name: string;
      status: string;
      qualifying_sessions: number;
      sessions_required: number;
    }> = [];
    for (const c of body.certifications) {
      if (
        c &&
        typeof c === "object" &&
        typeof (c as { name?: unknown }).name === "string" &&
        typeof (c as { status?: unknown }).status === "string" &&
        typeof (c as { qualifying_sessions?: unknown }).qualifying_sessions ===
          "number" &&
        typeof (c as { sessions_required?: unknown }).sessions_required ===
          "number"
      ) {
        valid.push({
          name: (c as { name: string }).name,
          status: (c as { status: string }).status,
          qualifying_sessions: (c as { qualifying_sessions: number })
            .qualifying_sessions,
          sessions_required: (c as { sessions_required: number })
            .sessions_required,
        });
      }
    }
    certifications = valid.length > 0 ? valid : null;
  }

  const welder = { name: welderName };
  const score = { total };
  const feedback = {
    summary: body.feedback.summary ?? "",
    feedback_items,
  };

  /** Optional top-bar meta; validate strings, max 128 chars each. */
  let sessionDate: string | undefined;
  if (body.sessionDate != null && typeof body.sessionDate === "string") {
    sessionDate = body.sessionDate.slice(0, 128) || undefined;
  }
  let duration: string | undefined;
  if (body.duration != null && typeof body.duration === "string") {
    duration = body.duration.slice(0, 128) || undefined;
  }
  let station: string | undefined;
  if (body.station != null && typeof body.station === "string") {
    station = body.station.slice(0, 128) || undefined;
  }

  let rework_cost_usd: number | null = null;
  if (
    body.rework_cost_usd != null &&
    typeof body.rework_cost_usd === "number" &&
    Number.isFinite(body.rework_cost_usd) &&
    body.rework_cost_usd >= 0
  ) {
    rework_cost_usd = body.rework_cost_usd;
  }

  let disposition: string | null = null;
  if (body.disposition != null && typeof body.disposition === "string") {
    disposition = body.disposition.slice(0, 32);
  }

  let agentInsights: WelderReportPDFProps["agentInsights"] = null;
  if (Array.isArray(body.agentInsights)) {
    agentInsights = body.agentInsights
      .filter(
        (r): r is { agent_name: string } =>
          r != null &&
          typeof r === "object" &&
          typeof (r as Record<string, unknown>).agent_name === "string"
      )
      .map((r) => {
        const obj = r as Record<string, unknown>;
        return {
          agent_name: String(obj.agent_name).slice(0, 64),
          disposition:
            typeof obj.disposition === "string"
              ? obj.disposition.slice(0, 32)
              : undefined,
          root_cause:
            typeof obj.root_cause === "string"
              ? obj.root_cause.slice(0, 500)
              : undefined,
          corrective_actions: Array.isArray(obj.corrective_actions)
            ? (obj.corrective_actions as unknown[]).filter(
                (s): s is string => typeof s === "string"
              )
            : undefined,
        };
      });
  }

  try {
    const pdfReact = React.createElement(WelderReportPDF, {
      welder,
      score,
      feedback,
      narrative,
      rework_cost_usd,
      disposition,
      agentInsights,
      sessionDate: sessionDate ?? undefined,
      duration: duration ?? undefined,
      station: station ?? undefined,
    });

    const buffer = await renderToBuffer(toPdfDoc(pdfReact));
    const filename = `${sanitizeFilename(welderName)}-warp-report.pdf`;

    return new Response(new Uint8Array(buffer), {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="${filename}"`,
      },
    });
  } catch (err) {
    logError("welder-report-pdf", err, { context: "PDF generation" });
    return NextResponse.json(
      { error: "PDF generation failed" },
      { status: 500 }
    );
  }
}
