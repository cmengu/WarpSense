/**
 * Prototype: @react-pdf/renderer renders WelderReportPDF to buffer.
 *
 * Run: npx tsx prototype/pdf-route.mts (after npm install @react-pdf/renderer)
 */
import React from "react";
import { renderToBuffer } from "@react-pdf/renderer";
import { WelderReportPDF } from "../src/components/pdf/WelderReportPDF";

/** WelderReportPDF returns <Document>; renderToBuffer expects Document root. Type assertion for TS. */
const toPdfDoc = (el: React.ReactElement) =>
  el as Parameters<typeof renderToBuffer>[0];

const SAMPLE_PROPS = {
  welder: { name: "Mike Chen" },
  score: { total: 75, rules: [] },
  feedback: {
    summary: "Good work",
    feedback_items: [
      {
        message: "Angle consistency improved",
        severity: "info",
        suggestion: null,
      },
    ],
  },
  chartDataUrl:
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
};

async function main() {
  const pdfReact = React.createElement(WelderReportPDF, SAMPLE_PROPS);
  const buffer = await renderToBuffer(toPdfDoc(pdfReact));

  const header = buffer.slice(0, 5).toString("utf8");
  if (header !== "%PDF-") {
    throw new Error(`Invalid PDF header: got ${header}`);
  }

  const str = buffer.toString("utf8");
  if (
    !str.includes("Mike Chen") ||
    !str.includes("75") ||
    !str.includes("Good work")
  ) {
    throw new Error("PDF missing expected content");
  }

  console.log(`Rendered PDF: ${buffer.length} bytes`);
  console.log("Content check: OK");

  // Malformed feedback_items
  const malformedProps = {
    ...SAMPLE_PROPS,
    feedback: {
      summary: "Test",
      feedback_items: [
        { message: "Valid", severity: "info" },
        { message: null, severity: undefined } as unknown as {
          message: string;
          severity: string;
        },
        { message: "Also valid", severity: "warning" },
      ],
    },
  };
  const malformedBuffer = await renderToBuffer(
    toPdfDoc(React.createElement(WelderReportPDF, malformedProps))
  );
  const ms = malformedBuffer.toString("utf8");
  if (!ms.includes("Valid") || !ms.includes("Also valid")) {
    throw new Error("Malformed feedback_items should skip invalid item");
  }

  // welder.name as object — should coerce to "Unknown" (toWelderName)
  const badNameProps = {
    ...SAMPLE_PROPS,
    welder: {
      name: { first: "Mike", last: "Chen" },
    } as unknown as { name: string },
  };
  const badNameBuffer = await renderToBuffer(
    toPdfDoc(React.createElement(WelderReportPDF, badNameProps))
  );
  const badStr = badNameBuffer.toString("utf8");
  if (badStr.includes("[object Object]")) {
    throw new Error("welder.name object should not produce [object Object]");
  }

  process.exit(0);
}
main().catch((e) => {
  console.error(e);
  process.exit(1);
});
