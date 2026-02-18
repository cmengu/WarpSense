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
import { logError } from "@/lib/logger";
import { WelderReportPDF } from "@/components/pdf/WelderReportPDF";
import type { SessionScore } from "@/lib/api";

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

  const welder = { name: welderName };
  const score = { total, rules: body.score.rules ?? [] };
  const feedback = {
    summary: body.feedback.summary ?? "",
    feedback_items,
  };

  try {
    const pdfReact = React.createElement(WelderReportPDF, {
      welder,
      score,
      feedback,
      chartDataUrl,
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
