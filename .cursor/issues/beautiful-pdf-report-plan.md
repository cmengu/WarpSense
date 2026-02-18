# Beautiful PDF Report — Implementation Plan (Refined v5)

**Issue:** `.cursor/issues/beautiful-pdf-report.md`  
**Exploration:** `.cursor/issues/beautiful-pdf-report-exploration.md`  
**Date:** 2026-02-18

---

## Phase Breakdown

### Phase 1 — Dependencies and PDF Component
**Goal:** Dependencies installed; PDF layout component exists and can render a test PDF in isolation.  
**Risk:** Low  
**Estimate:** 3.5h  

### Phase 2 — API Route and Validation
**Goal:** POST `/api/welder-report-pdf` accepts valid payload, renders PDF, returns attachment. Returns 400 on missing welder/score/feedback, type errors, invalid feedback_items, oversized chartDataUrl, oversized body, invalid Content-Length, non-string welder.name, and non-PNG chartDataUrl. Returns 411 when chunked without Content-Length. Returns 413 when body > 5MB.  
**Risk:** Medium (React PDF + Next.js 16 compatibility)  
**Estimate:** 5.5h  

### Phase 3 — Client Integration and Download Flow
**Goal:** Welder page has chart wrapper with `id="trend-chart"`; Download PDF button captures chart, POSTs to API, triggers download with loading/error state. Uses basePath-aware fetch when configured. Orphaned toPng promise prevented.  
**Risk:** Medium (html-to-image on Recharts)  
**Estimate:** 5h  

### Phase 4 — Tests and Edge Cases
**Goal:** Unit tests updated; validation and edge cases covered; fetch restored in afterEach; API test runs in Node; chart fallback test with isolated toPng mock; trend-chart element assertion with 600×200 dimensions; getApiBase testable in Node and jsdom (basePath branch exercised); toWelderName invariant test; CI-friendly memory limits (413 skip when CI_LOW_MEM=1).  
**Risk:** Low  
**Estimate:** 4h  

---

## Steps

### Phase 1 — Dependencies and PDF Component

---

**Step 1.1 — Install dependencies**

*What:* Add `@react-pdf/renderer` and `html-to-image` to package.json with exact pinned versions. Use `--save-exact`. Use `npm ci` for subsequent installs to prevent lockfile drift. Ensure package-lock.json is committed. **Add automated pre-Phase-2 check that fails if package-lock.json has uncommitted changes.**

*File:* `my-app/package.json` (modify via `npm install`)

*Depends on:* none

*Code:*
```bash
cd my-app && npm install --save-exact @react-pdf/renderer@3.4.0 html-to-image@1.11.11
# Commit lockfile if changed: git add package-lock.json && git commit -m "chore: lock pdf dependencies"
```

*Why this approach:* Spec mandates @react-pdf/renderer; exploration chose Option A (html-to-image). Exact pinning prevents lockfile regeneration from pulling incompatible versions. Adversarial: lockfile must be committed for npm ci. Automated check prevents CI/local divergence.

*Verification:*
```
Setup: cd my-app (or repo root for monorepo; expected cwd: directory containing my-app/)
Action: npm ci && grep -E '"@react-pdf/renderer"|"html-to-image"' package.json
Expected: Both packages in dependencies with exact versions (no ^)
Pass criteria:
  [ ] @react-pdf/renderer in dependencies (exact, e.g. "3.4.0" not "^3.4.0")
  [ ] html-to-image in dependencies (exact)
  [ ] npm ci completes without error
  [ ] package-lock.json exists and is committed (git status my-app/package-lock.json shows nothing to commit)
  [ ] Automated check (run before Phase 2): git diff --quiet my-app/package-lock.json || { echo "FAIL: package-lock.json has uncommitted changes"; exit 1; }
If it fails: Check network; verify Node/npm; run npm cache clean --force; commit lockfile
```

*Estimate:* 0.25h  

---

**Step 1.2 — Create PDF component directory and WelderReportPDF.tsx**

*What:* Create `components/pdf/WelderReportPDF.tsx` with Document, Page, View, Text, Image, StyleSheet. Accepts welder, score, feedback, chartDataUrl. Dark theme (#0a0a0a). Fix spec typos: `leerSpacing` → letterSpacing, `lineHeght` → lineHeight. Add defensive rendering for feedback_items; sanitize text. **Only render Image when chartDataUrl is a string starting with `data:image/png`** — reject SVG/webp to prevent React PDF Image errors. **Coerce welder.name to string before use** (handles object/array from upstream bugs). **Use `trim()` consistently** — both component and API treat whitespace-only as "Unknown".

*File:* `my-app/src/components/pdf/WelderReportPDF.tsx` (create)

*Depends on:* Step 1.1

*Code:*
```typescript
import {
  Document,
  Page,
  View,
  Text,
  StyleSheet,
  Image,
} from "@react-pdf/renderer";

/** Sanitize text for PDF rendering. Strips control chars, zero-width, RTL-override. Defined in WelderReportPDF.tsx. */
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
  feedback: { summary: string; feedback_items: Array<{ message: string; severity: string; suggestion?: string | null }> };
  chartDataUrl?: string | null;
}

function isPngDataUrl(v: unknown): v is string {
  return typeof v === "string" && v.startsWith("data:image/png");
}

/** Coerce welder name to string; always returns string. Whitespace-only → "Unknown". Matches API route behavior. */
function toWelderName(v: unknown): string {
  if (typeof v === "string" && v.trim().length > 0) return v.trim();
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return "Unknown";
}

export function WelderReportPDF({
  welder,
  score,
  feedback,
  chartDataUrl,
}: WelderReportPDFProps) {
  const rawItems = feedback?.feedback_items ?? [];
  const validItems = rawItems.filter(
    (item): item is { message: string; severity: string; suggestion?: string | null } =>
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
            <Text style={styles.sectionTitle}>Score Trend (Last 5 Sessions)</Text>
            <Image src={chartPng} style={{ height: 120 }} />
          </View>
        )}

        <Text style={styles.sectionTitle}>Key Areas</Text>
        {top3.map((item, i) => (
          <View key={i} style={styles.feedbackItem}>
            <Text style={styles.bullet}>{item.severity === "warning" || item.severity === "critical" ? "⚠" : "•"}</Text>
            <View>
              <Text style={{ fontSize: 10, color: "#f9fafb" }}>{sanitizeText(item.message)}</Text>
              {item.suggestion && (
                <Text style={{ fontSize: 9, color: "#6b7280", marginTop: 2 }}>
                  → {sanitizeText(item.suggestion)}
                </Text>
              )}
            </View>
          </View>
        ))}

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
```

*Why this approach:* Adversarial: chartDataUrl SVG could slip through → React PDF throws. Only PNG accepted. welder.name object/array → toWelderName prevents '[object Object]'. Whitespace-only → trim consistently yields "Unknown" in both component and API (no render/filename divergence). sanitizeText strips zero-width and RTL override chars. Defensive filtering prevents 500 from malformed feedback_items.

*Verification:*
```
Setup: Step 1.1 done; my-app builds
Action: npx tsc --noEmit -p my-app
Expected: No type errors
Pass criteria:
  [ ] File exists at my-app/src/components/pdf/WelderReportPDF.tsx
  [ ] No TypeScript errors
  [ ] Component exports WelderReportPDF and WelderReportPDFProps
If it fails: Fix import paths; ensure @react-pdf/renderer types resolve
```

*Estimate:* 1h  

---

**Step 1.3 — Smoke test: render WelderReportPDF with renderToBuffer**

*What:* Update prototype to render `WelderReportPDF` with sample props. Add malformed feedback_items case. **Verification criteria aligned with actual code output** — no reference to "Large PNG (~130KB) PDF: OK" since that test is omitted. Add check that PDF is well-formed beyond header (content presence sufficient; full structural validation via pdf-parse is optional enhancement noted in Known Issues). **Note:** `buffer.toString("utf8").includes("Mike Chen")` is heuristic; @react-pdf/renderer may emit compressed or hex-encoded text in future versions — if Step 1.3 fails after dependency update, verify PDF visually and consider pdf-parse for programmatic content check.

*File:* `my-app/prototype/pdf-route.mts` (modify)

*Depends on:* Step 1.1, 1.2

*Code:*
```typescript
/**
 * Prototype: @react-pdf/renderer renders WelderReportPDF to buffer.
 *
 * Run: npx tsx prototype/pdf-route.mts (after npm install @react-pdf/renderer)
 */
import React from "react";
import { renderToBuffer } from "@react-pdf/renderer";
import { WelderReportPDF } from "../src/components/pdf/WelderReportPDF";

const SAMPLE_PROPS = {
  welder: { name: "Mike Chen" },
  score: { total: 75, rules: [] },
  feedback: {
    summary: "Good work",
    feedback_items: [
      { message: "Angle consistency improved", severity: "info", suggestion: null },
    ],
  },
  chartDataUrl: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
};

async function main() {
  const pdfReact = React.createElement(WelderReportPDF, SAMPLE_PROPS);
  const buffer = await renderToBuffer(pdfReact);

  const header = buffer.slice(0, 5).toString("utf8");
  if (header !== "%PDF-") {
    throw new Error(`Invalid PDF header: got ${header}`);
  }

  const str = buffer.toString("utf8");
  if (!str.includes("Mike Chen") || !str.includes("75") || !str.includes("Good work")) {
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
        { message: null, severity: undefined } as unknown as { message: string; severity: string },
        { message: "Also valid", severity: "warning" },
      ],
    },
  };
  const malformedBuffer = await renderToBuffer(React.createElement(WelderReportPDF, malformedProps));
  const ms = malformedBuffer.toString("utf8");
  if (!ms.includes("Valid") || !ms.includes("Also valid")) {
    throw new Error("Malformed feedback_items should skip invalid item");
  }

  // welder.name as object — should coerce to "Unknown" (toWelderName)
  const badNameProps = {
    ...SAMPLE_PROPS,
    welder: { name: { first: "Mike", last: "Chen" } } as unknown as { name: string },
  };
  const badNameBuffer = await renderToBuffer(React.createElement(WelderReportPDF, badNameProps));
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
```

*Why this approach:* Adversarial: verification criteria must match code output. Removed "Large PNG (~130KB) PDF: OK" from pass criteria. Added welder.name object test to validate toWelderName. Phase 1→2 boundary: prototype uses WelderReportPDF (full replacement of minimal Doc). PDF text search assumes react-pdf emits plain UTF-8; if version changes output format, Step 1.3 may need pdf-parse or visual verification.

*Verification:*
```
Setup: npm install done; WelderReportPDF exists
Action: cd my-app && npx tsx prototype/pdf-route.mts
Expected: "Rendered PDF: N bytes", "Content check: OK"; exit 0
Pass criteria:
  [ ] Command exits 0
  [ ] Output contains "Rendered PDF" and "Content check: OK"
  [ ] Malformed feedback_items case completes
  [ ] welder.name object case completes (no [object Object])
If it fails: Check @react-pdf/renderer version; ensure import resolves; if react-pdf changed output format, use pdf-parse or visual verification
```

*Estimate:* 0.5h  

---

### Phase 2 — API Route and Validation

---

**Step 2.1 — Create API route with validation and body size limit**

*What:* Create `src/app/api/welder-report-pdf/route.ts` (route path: `my-app/src/app/api/welder-report-pdf/route.ts`). POST handler:

1. **Content-Length check when present:** Reject 400 if non-numeric or negative; reject 413 if > 5MB.
2. **Chunked encoding:** When `Transfer-Encoding: chunked` is present without Content-Length, reject immediately with 411 Length Required (or 431 if client should retry with Content-Length). **Document:** 5MB limit applies only when Content-Length is sent; chunked requests are rejected to prevent OOM. If Accept-Chunked is required for large uploads, implement streaming parser with size cap (out of scope for MVP).
3. Parse JSON with try/catch → 400.
4. **Validate welder.name is string:** `if (typeof body.welder.name !== 'string' || body.welder.name.trim() === '')` → use "Unknown" or reject 400. Prevents [object Object] in PDF and filename.
5. Validate welder/score/feedback.
6. **Explicit type check:** `if (typeof chartDataUrl !== 'string') chartDataUrl = null` before length check.
7. Validate chartDataUrl max 2MB; **reject non-PNG data URLs**.
8. Call renderToBuffer, return PDF. **Filename: use `sanitizeDownloadFilename(toWelderName(welderName))`** — ensures toWelderName always returns string before sanitize.

*File:* `my-app/src/app/api/welder-report-pdf/route.ts` (create)

*Depends on:* Step 1.2, 1.3

*Code:*
```typescript
import { NextResponse } from "next/server";
import { renderToBuffer } from "@react-pdf/renderer";
import React from "react";
import { WelderReportPDF } from "@/components/pdf/WelderReportPDF";
import type { SessionScore } from "@/lib/api";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

interface PDFRequestBody {
  welder?: { name?: unknown };
  score?: SessionScore;
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

function isValidFeedbackItem(item: unknown): item is { message: string; severity: string; suggestion?: string | null } {
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
    // Chunked encoding without Content-Length: we cannot safely cap size before reading.
    // Reject to prevent OOM from oversized chunked body.
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
        { error: `Request body exceeds max size (${MAX_BODY_SIZE_BYTES} bytes)` },
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
      { error: "Each feedback item must have non-empty message and severity (string)" },
      { status: 400 }
    );
  }

  let chartDataUrl: string | null = null;
  if (body.chartDataUrl != null && typeof body.chartDataUrl === "string") {
    if (!body.chartDataUrl.startsWith("data:image/png")) {
      chartDataUrl = null;
    } else if (body.chartDataUrl.length > MAX_CHART_DATA_URL_LENGTH) {
      return NextResponse.json(
        { error: `chartDataUrl exceeds max length (${MAX_CHART_DATA_URL_LENGTH} bytes)` },
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

    const buffer = await renderToBuffer(pdfReact);
    const filename = `${sanitizeFilename(welderName)}-warp-report.pdf`;

    return new Response(buffer, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="${filename}"`,
      },
    });
  } catch (err) {
    console.error("PDF generation failed:", err);
    return NextResponse.json(
      { error: "PDF generation failed" },
      { status: 500 }
    );
  }
}
```

*Why this approach:* Adversarial: chunked encoding bypasses Content-Length → reject chunked. welder.name object → toWelderName. chartDataUrl type coercion, non-PNG rejection. Filename uses welderName from toWelderName (always string).

*Verification:*
```
Setup: Dev server on localhost:3000 (see Pre-Flight below)
Action: curl -X POST http://localhost:3000/api/welder-report-pdf \
  -H "Content-Type: application/json" \
  -d '{"welder":{"name":"Mike Chen"},"score":{"total":75,"rules":[]},"feedback":{"summary":"Good work","feedback_items":[{"message":"Test","severity":"info","suggestion":null}]}}' \
  -o /tmp/test.pdf && file /tmp/test.pdf
Expected: /tmp/test.pdf: PDF document
Pass criteria:
  [ ] HTTP 200
  [ ] Content-Type: application/pdf
  [ ] file /tmp/test.pdf reports "PDF document"
  [ ] head -c 5 /tmp/test.pdf | xxd → 25 50 44 46 2d
If it fails: Check route path; ensure runtime is nodejs
```

*Estimate:* 2h  

**Classification:** CRITICAL

---

**Step 2.2 — Verify 400 on missing welder**

*What:* Curl with missing welder; assert 400 and error body. Use `jq -r .error` for robust parsing when available.

*File:* (verification only)

*Depends on:* Step 2.1

*Code:*
```bash
RESP=$(curl -s -X POST http://localhost:3000/api/welder-report-pdf \
  -H "Content-Type: application/json" \
  -d '{"score":{"total":75,"rules":[]},"feedback":{"summary":"","feedback_items":[]}}')
HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:3000/api/welder-report-pdf \
  -H "Content-Type: application/json" \
  -d '{"score":{"total":75,"rules":[]},"feedback":{"summary":"","feedback_items":[]}}')
ERR=$(echo "$RESP" | jq -r '.error // empty' 2>/dev/null || echo "$RESP" | grep -oE '"error":"[^"]*"' | head -1)
test "$HTTP" = "400" || { echo "Expected 400 got $HTTP"; exit 1; }
( [ -n "$ERR" ] || echo "$RESP" | grep -qiE "welder|missing|invalid" ) && echo "PASS"
```

*Verification:*
```
Setup: Dev server running
Action: Run script above
Expected: HTTP 400; body contains welder/Missing/invalid
Pass criteria:
  [ ] HTTP 400
  [ ] Response body has .error or matches welder|Missing|invalid
If it fails: Add welder validation
```

*Estimate:* 0.25h  

---

**Step 2.3 — Verify 400 on other validation paths, 411 on chunked, 413 on oversized body**

*What:* Verify 400 on missing score, feedback, type errors, invalid feedback_items, non-string welder.name, oversized chartDataUrl, non-PNG chartDataUrl. Verify 411 on chunked without Content-Length. Verify 413 on Content-Length > 5MB. **Every case must capture HTTP status and assert expected code** — curl returns exit 0 for HTTP 400/413; script must fail if status is wrong. **Assert BIG length > 2*1024*1024 before curl** — ensures oversized chartDataUrl test actually sends payload exceeding limit.

*File:* (verification only)

*Depends on:* Step 2.1

*Code:*
```bash
set -e
BASE="http://localhost:3000/api/welder-report-pdf"
VALID='{"welder":{"name":"X"},"score":{"total":75,"rules":[]},"feedback":{"summary":"","feedback_items":[{"message":"X","severity":"info"}]}}'

# Missing score → 400
HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE" -H "Content-Type: application/json" \
  -d "{\"welder\":{\"name\":\"X\"},\"feedback\":{\"summary\":\"\",\"feedback_items\":[{\"message\":\"X\",\"severity\":\"info\"}]}}")
test "$HTTP" = "400" || { echo "Missing score: expected 400 got $HTTP"; exit 1; }

# welder.name as object → toWelderName produces "Unknown"; PDF valid
HTTP_OBJ=$(curl -s -o /tmp/obj.pdf -w "%{http_code}" -X POST "$BASE" -H "Content-Type: application/json" \
  -d '{"welder":{"name":{"first":"Mike"}},"score":{"total":75,"rules":[]},"feedback":{"summary":"","feedback_items":[{"message":"X","severity":"info"}]}}')
test "$HTTP_OBJ" = "200" || { echo "Expected 200 for welder.name object, got $HTTP_OBJ"; exit 1; }
file /tmp/obj.pdf | grep -q "PDF document"
grep -q 'Unknown' /tmp/obj.pdf || { echo "PDF should contain Unknown"; exit 1; }
! grep -q '\[object Object\]' /tmp/obj.pdf || { echo "PDF must not contain [object Object]"; exit 1; }

# score.total string → 400
HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE" -H "Content-Type: application/json" \
  -d '{"welder":{"name":"X"},"score":{"total":"75","rules":[]},"feedback":{"summary":"","feedback_items":[{"message":"X","severity":"info"}]}}')
test "$HTTP" = "400" || { echo "score.total string: expected 400 got $HTTP"; exit 1; }

# Malformed JSON → 400
HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE" -H "Content-Type: application/json" -d 'not json')
test "$HTTP" = "400" || { echo "Malformed JSON: expected 400 got $HTTP"; exit 1; }

# Oversized chartDataUrl → 400 (assert BIG length > 2MB before curl)
BIG=$(node -e "console.log('A'.repeat(2100001))")
BIG_LEN=${#BIG}
REQUIRED_LEN=$((2*1024*1024))
test "$BIG_LEN" -gt "$REQUIRED_LEN" || { echo "BIG payload length $BIG_LEN must exceed $REQUIRED_LEN"; exit 1; }
RESP=$(curl -s -X POST "$BASE" -H "Content-Type: application/json" \
  -d "{\"welder\":{\"name\":\"X\"},\"score\":{\"total\":75,\"rules\":[]},\"feedback\":{\"summary\":\"\",\"feedback_items\":[{\"message\":\"X\",\"severity\":\"info\"}]},\"chartDataUrl\":\"data:image/png;base64,${BIG}\"}")
HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE" -H "Content-Type: application/json" \
  -d "{\"welder\":{\"name\":\"X\"},\"score\":{\"total\":75,\"rules\":[]},\"feedback\":{\"summary\":\"\",\"feedback_items\":[{\"message\":\"X\",\"severity\":\"info\"}]},\"chartDataUrl\":\"data:image/png;base64,${BIG}\"}")
test "$HTTP" = "400" || { echo "Oversized chartDataUrl: expected 400 got $HTTP"; exit 1; }
echo "$RESP" | jq -r '.error // empty' 2>/dev/null | grep -qE "chartDataUrl|exceeds" || echo "$RESP" | grep -qE "chartDataUrl|exceeds" || true

# Non-PNG chartDataUrl → silently null (PDF without chart)
curl -s -X POST "$BASE" -H "Content-Type: application/json" \
  -d '{"welder":{"name":"X"},"score":{"total":75,"rules":[]},"feedback":{"summary":"","feedback_items":[{"message":"X","severity":"info"}]},"chartDataUrl":"data:image/svg+xml;base64,PHN2Zy8+"}' -o /tmp/svg.pdf
file /tmp/svg.pdf
test -f /tmp/svg.pdf && grep -q "PDF" /tmp/svg.pdf 2>/dev/null || file /tmp/svg.pdf | grep -q "PDF document"

# 411 on chunked without Content-Length (if possible to simulate)
# Note: curl -d typically adds Content-Length; Request API also adds it. 411 branch is defensive code;
# standard HTTP clients may never trigger it. Document as defensive-only.
HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE" -H "Content-Type: application/json" -H "Transfer-Encoding: chunked" -d '{"welder":{"name":"X"},"score":{"total":75,"rules":[]},"feedback":{"summary":"","feedback_items":[{"message":"X","severity":"info"}]}}')
test "$HTTP" = "411" || test "$HTTP" = "400" || { echo "Chunked: expected 411 or 400 got $HTTP"; exit 1; }

# 413 on oversized body (Content-Length > 5MB)
# Skip when CI_LOW_MEM=1 AND (CI=true or CI=1); document CI env format in Known Issues
if [ "${CI_LOW_MEM}" = "1" ] && { [ "${CI}" = "true" ] || [ "${CI}" = "1" ]; }; then
  echo "Skipping 413 test (CI_LOW_MEM=1)"
else
  HTTP413=$(node -e "
const len = 5*1024*1024 + 1024;
const payload = JSON.stringify({ welder:{name:'X'}, score:{total:75,rules:[]}, feedback:{summary:'',feedback_items:[{message:'X',severity:'info'}]}, pad: 'x'.repeat(len) });
require('http').request({
  host:'localhost', port:3000, path:'/api/welder-report-pdf', method:'POST',
  headers:{'Content-Type':'application/json','Content-Length':String(Buffer.byteLength(payload))}
}, r => {
  let d='';
  r.on('data',c=>d+=c);
  r.on('end',()=>{ process.stdout.write(String(r.statusCode)); });
}).end(payload);
")
  test "$HTTP413" = "413" || { echo "413 body: expected 413 got $HTTP413"; exit 1; }
fi

echo "All Step 2.3 validation checks passed"
```

*Verification:*
```
Setup: Dev server running
Action: Run curl/node commands
Expected: 400 for validation failures; 411 for chunked (when testable); 413 for body > 5MB; SVG chartDataUrl produces valid PDF without chart; welder.name object produces valid PDF (no [object Object])
Pass criteria:
  [ ] Missing score: 400 (asserted)
  [ ] score.total string: 400 (asserted)
  [ ] Malformed JSON: 400 (asserted)
  [ ] Oversized chartDataUrl: 400 (asserted); BIG length > 2MB verified before curl
  [ ] SVG chartDataUrl: 200, PDF valid (chart omitted)
  [ ] Body > 5MB: 413 (asserted, or skipped when CI_LOW_MEM=1 and CI=true or CI=1)
  [ ] welder.name object: 200, PDF valid, grep finds "Unknown", grep does not find "[object Object]"
If it fails: Add corresponding validation
```

*Estimate:* 0.5h  

---

### Phase 3 — Client Integration and Download Flow

---

**Step 3.1 — Add id="trend-chart" wrapper with fixed dimensions around LineChart**

*What:* Wrap LineChart in a div with `id="trend-chart"`, fixed width 600, height 200. **Use inline style** (width: 600, height: 200) — avoid Tailwind/class-based dimensions that parent CSS could override via !important; inline style ensures html-to-image captures intended dimensions. **Note:** Parent CSS (dark mode, !important) could still override; Step 4.4 asserts dimensions; if capture produces wrong aspect ratio, inspect for conflicting CSS.

*File:* `my-app/src/app/seagull/welder/[id]/page.tsx` (modify)

*Depends on:* none

*Code:*
```tsx
      <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-bold mb-4">Progress Over Time</h2>
        <div
          id="trend-chart"
          style={{ width: 600, height: 200 }}
          data-testid="trend-chart"
        >
          <LineChart data={MOCK_HISTORICAL} color="#3b82f6" height={200} />
        </div>
      </div>
```

*Why this approach:* Exploration: id and fixed dimensions for html-to-image. data-testid enables automated assertion. Inline style preferred for predictable capture; avoid CSS classes that could be overridden.

*Verification:*
```
Setup: Dev server running
Action: Open /seagull/welder/mike-chen; DevTools: document.getElementById('trend-chart')?.offsetWidth
Expected: 600
Pass criteria:
  [ ] document.getElementById('trend-chart') exists
  [ ] Element 600×200 (inline style; offsetWidth 600 when no CSS override)
  [ ] LineChart renders inside
If it fails: Ensure id and style on correct wrapper; check for conflicting parent CSS
```

*Estimate:* 0.25h  

---

**Step 3.2 — Create captureChartToBase64 helper with orphaned-promise fix**

*What:* Add `captureChartToBase64` in `lib/pdf-chart-capture.ts`. Use html-to-image toPng with 10s timeout. **When timeout wins, attach `.catch(() => {})` to the toPng promise to prevent unhandledrejection** (adversarial critical fix).

*File:* `my-app/src/lib/pdf-chart-capture.ts` (create)

*Depends on:* Step 1.1

*Code:*
```typescript
import { toPng } from "html-to-image";

const CAPTURE_TIMEOUT_MS = 10_000;

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T | null> {
  let timeoutId: ReturnType<typeof setTimeout>;
  const timeout = new Promise<null>((_, reject) => {
    timeoutId = setTimeout(() => reject(new Error("Capture timeout")), ms);
  });
  const raced = Promise.race([promise, timeout]).finally(() => clearTimeout(timeoutId));
  return raced;
}

/**
 * Capture a DOM element to base64 PNG.
 * Returns null if element not found, capture fails, or times out.
 * When timeout wins, the toPng promise continues — attach .catch to prevent unhandledrejection.
 */
export async function captureChartToBase64(elementId: string): Promise<string | null> {
  const el = document.getElementById(elementId);
  if (!el) return null;
  const toPngPromise = toPng(el, { cacheBust: true, pixelRatio: 2 });
  toPngPromise.catch(() => {}); // Prevent unhandledrejection when timeout wins and toPng later rejects
  try {
    const result = await withTimeout(toPngPromise, CAPTURE_TIMEOUT_MS);
    return result;
  } catch {
    return null;
  }
}
```

*Why this approach:* Adversarial: orphaned toPng promise on timeout → unhandledrejection. Attaching .catch(() => {}) silences the eventual reject.

*Verification:*
```
Setup: my-app builds
Action: npx tsc --noEmit -p my-app
Expected: No errors
Pass criteria:
  [ ] File compiles
  [ ] toPng.catch(() => {}) present
If it fails: Check html-to-image types
```

*Estimate:* 0.5h  

---

**Step 3.3 — Extract getApiBase to lib and add handleDownloadPDF**

*What:* Create `lib/api-base.ts` with `getApiBase()` (testable). Add pdfLoading, pdfError state and handleDownloadPDF to welder page. Use getApiBase() for fetch URL. Map report→feedback, score from fetchScore. Disable button when pdfLoading or loading. Show pdfError inline. **Invariant: `welderName = toWelderName(displayName)` — always string before `sanitizeDownloadFilename(welderName)`.**

*File:* `my-app/src/lib/api-base.ts` (create), `my-app/src/app/seagull/welder/[id]/page.tsx` (modify)

*Depends on:* Step 3.1, 3.2, 2.1

*Code for api-base.ts:*
```typescript
/**
 * Base path for API requests when Next.js basePath is configured.
 * Set NEXT_PUBLIC_BASE_PATH at build time to match next.config basePath.
 * Note: Next.js inlines NEXT_PUBLIC_* at build; unit test mutates process.env in Node
 * and may not reflect real browser behavior. See Known Issues.
 */
export function getApiBase(): string {
  if (typeof window === "undefined") return "";
  const base = (typeof process !== "undefined" && (process.env as { NEXT_PUBLIC_BASE_PATH?: string })?.NEXT_PUBLIC_BASE_PATH) ?? "";
  return String(base).replace(/\/$/, "");
}
```

*Code for page.tsx (additions):*
```typescript
import { captureChartToBase64 } from "@/lib/pdf-chart-capture";
import { getApiBase } from "@/lib/api-base";

/** Coerce welder name to string; always returns string. Matches API route. */
function toWelderName(v: unknown): string {
  if (typeof v === "string" && v.trim().length > 0) return v.trim();
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return "Unknown";
}

function sanitizeDownloadFilename(name: string): string {
  const s = String(name).replace(/[^a-zA-Z0-9_-]/g, "-").slice(0, 64) || "welder";
  return `${s}-warp-report.pdf`;
}

// Add state:
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);

// Add handler:
  async function handleDownloadPDF() {
    if (!report || !score) return;
    setPdfError(null);
    setPdfLoading(true);
    try {
      const chartDataUrl = await captureChartToBase64("trend-chart");

      const welderName = toWelderName(displayName);
      const payload = {
        welder: { name: welderName },
        score: { total: score.total, rules: score.rules },
        feedback: {
          summary: report.summary,
          feedback_items: report.feedback_items,
        },
        chartDataUrl,
      };

      const apiUrl = `${getApiBase()}/api/welder-report-pdf`;
      const res = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { error?: string }).error ?? `Failed to generate PDF (${res.status})`);
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = sanitizeDownloadFilename(welderName);
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setPdfError(err instanceof Error ? err.message : String(err));
      logError("WelderReport", err, { context: "handleDownloadPDF" });
    } finally {
      setPdfLoading(false);
    }
  }

// Update button:
        <button
          className="bg-zinc-200 text-zinc-800 px-6 py-3 rounded-lg font-semibold hover:bg-zinc-300 dark:bg-zinc-700 dark:text-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={handleDownloadPDF}
          disabled={loading || pdfLoading}
        >
          {pdfLoading ? "⏳ Generating..." : "📄 Download PDF"}
        </button>

// Add error display:
      {pdfError && (
        <p className="mt-4 text-red-600 dark:text-red-400 text-sm">{pdfError}</p>
      )}
```

*Why this approach:* Critique: basePath not asserted. Extracting getApiBase enables unit test. Known: NEXT_PUBLIC_BASE_PATH must match next.config basePath at build. Manual smoke: Remove id=trend-chart via DevTools; click; PDF downloads without chart — document before demo.

*Verification:*
```
Setup: Dev server; /seagull/welder/mike-chen loads
Action: Click "Download PDF"
Expected: Button shows "Generating..."; file downloads; filename Mike-Chen-warp-report.pdf
Pass criteria:
  [ ] Button disabled during generation
  [ ] PDF downloads with correct content
  [ ] Manual smoke (before demo): Remove id="trend-chart" via DevTools; click Download; PDF downloads without chart (no error placeholder)
If it fails: Check fetch URL; payload shape; displayName
```

*Estimate:* 1.5h  

**Classification:** CRITICAL

---

### Phase 4 — Tests and Edge Cases

---

**Step 4.1 — Mock fetch and html-to-image; assert POST on Download PDF click**

*What:* Replace Download PDF alert test with fetch mock. Mock html-to-image toPng. Assert fetch called with POST to /api/welder-report-pdf, body contains welder, score, feedback. **Restore global.fetch in afterEach.**

*File:* `my-app/src/__tests__/app/seagull/welder/[id]/page.test.tsx` (modify)

*Depends on:* Step 3.3

*Code:*
```typescript
jest.mock("html-to-image", () => ({
  toPng: jest.fn().mockResolvedValue("data:image/png;base64,fake"),
}));

// In describe("Download PDF") or new section:
  describe("Download PDF", () => {
    let originalFetch: typeof global.fetch;

    beforeEach(() => {
      originalFetch = global.fetch;
    });

    afterEach(() => {
      global.fetch = originalFetch;
    });

    it("POSTs to API with correct payload", async () => {
      const mockBlob = new Blob(["pdf"], { type: "application/pdf" });
      const mockFetch = jest.fn().mockResolvedValue({ ok: true, blob: () => Promise.resolve(mockBlob) });
      global.fetch = mockFetch as typeof fetch;

      render(<WelderReportPage params={{ id: "mike-chen" }} />);
      await waitFor(() => expect(screen.getByText(/75\/100/)).toBeInTheDocument());

      fireEvent.click(screen.getByRole("button", { name: /Download PDF/i }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining("/api/welder-report-pdf"),
          expect.objectContaining({ method: "POST", headers: { "Content-Type": "application/json" } })
        );
      });

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.welder).toEqual({ name: "Mike Chen" });
      expect(body.score.total).toBe(75);
      expect(body.feedback).toBeDefined();
    });
  });
```

*Verification:*
```
Setup: cd my-app
Action: npm test -- --testPathPattern="welder/\[id\]/page" --runInBand
Expected: Test passes
Pass criteria:
  [ ] POSTs to API passes
  [ ] No alert test for Download PDF
  [ ] All other tests pass
If it fails: Adjust mocks
```

*Estimate:* 1h  

**Classification:** CRITICAL

---

**Step 4.2 — Assert button disabled when pdfLoading**

*What:* Same describe block. Defer fetch resolve; assert button disabled during generation.

*File:* `my-app/src/__tests__/app/seagull/welder/[id]/page.test.tsx` (modify)

*Depends on:* Step 4.1

*Code:*
```typescript
    it("Download PDF button is disabled during generation", async () => {
      let resolveFetch: (v: { ok: boolean; blob: () => Promise<Blob> }) => void;
      const fetchPromise = new Promise<{ ok: boolean; blob: () => Promise<Blob> }>((r) => { resolveFetch = r; });
      const mockFetch = jest.fn().mockReturnValue(fetchPromise);
      const orig = global.fetch;
      global.fetch = mockFetch as typeof fetch;
      try {
        render(<WelderReportPage params={{ id: "mike-chen" }} />);
        await waitFor(() => expect(screen.getByText(/75\/100/)).toBeInTheDocument());
        const btn = screen.getByRole("button", { name: /Download PDF/i });
        fireEvent.click(btn);
        await waitFor(() => expect(btn).toBeDisabled());
        resolveFetch!({ ok: true, blob: () => Promise.resolve(new Blob()) });
      } finally {
        global.fetch = orig;
      }
    });
```

*Verification:*
```
Action: npm test -- --testPathPattern="welder/\[id\]/page"
Expected: Pass
Pass criteria:
  [ ] Button disabled during fetch
If it fails: Defer resolveFetch until after click
```

*Estimate:* 0.5h  

---

**Step 4.3 — Chart fallback test with isolated toPng null mock**

*What:* Test that when toPng returns null, fetch body contains chartDataUrl: null. **Use try/finally to restore the default toPng mock** — prevents mock bleed (critique fix).

*File:* `my-app/src/__tests__/app/seagull/welder/[id]/page.test.tsx` (modify)

*Depends on:* Step 4.1

*Code:*
```typescript
    it("sends chartDataUrl null when chart capture fails", async () => {
      const { toPng } = require("html-to-image");
      (toPng as jest.Mock).mockResolvedValue(null);

      const mockBlob = new Blob(["pdf"], { type: "application/pdf" });
      const mockFetch = jest.fn().mockResolvedValue({ ok: true, blob: () => Promise.resolve(mockBlob) });
      const orig = global.fetch;
      global.fetch = mockFetch as typeof fetch;

      try {
        render(<WelderReportPage params={{ id: "mike-chen" }} />);
        await waitFor(() => expect(screen.getByText(/75\/100/)).toBeInTheDocument());
        fireEvent.click(screen.getByRole("button", { name: /Download PDF/i }));
        await waitFor(() => expect(mockFetch).toHaveBeenCalled());

        const body = JSON.parse(mockFetch.mock.calls[0][1].body);
        expect(body.chartDataUrl).toBeNull();
      } finally {
        global.fetch = orig;
        (toPng as jest.Mock).mockResolvedValue("data:image/png;base64,fake");
      }
    });
```

*Verification:*
```
Action: npm test -- --testPathPattern="welder/\[id\]/page"
Expected: Pass
Pass criteria:
  [ ] chartDataUrl is null in fetch body
  [ ] No mock bleed to other tests
If it fails: Restore toPng in finally
```

*Estimate:* 0.25h  

---

**Step 4.4 — Assert trend-chart element exists with 600×200 dimensions**

*What:* Add test that after report loads, element with id="trend-chart" (or data-testid="trend-chart") exists. **Assert style attribute contains width 600 and height 200** — guards against wrong chart capture dimensions (Step 3.1 specifies 600×200 for html-to-image). **Optionally assert computed dimensions** (`chartEl.offsetWidth === 600 && chartEl.offsetHeight === 200`) when element is rendered in jsdom — stronger invariant than style string; add if jsdom provides reliable layout.

*File:* `my-app/src/__tests__/app/seagull/welder/[id]/page.test.tsx` (modify)

*Depends on:* Step 3.1

*Code:*
```typescript
    it("renders trend-chart wrapper with 600×200 for PDF capture", async () => {
      render(<WelderReportPage params={{ id: "mike-chen" }} />);
      await waitFor(() => expect(screen.getByText(/75\/100/)).toBeInTheDocument());

      const chartEl = document.getElementById("trend-chart") ?? screen.getByTestId("trend-chart");
      expect(chartEl).toBeInTheDocument();
      const style = chartEl.getAttribute("style") ?? "";
      expect(style).toMatch(/width.*600|600.*width/i);
      expect(style).toMatch(/height.*200|200.*height/i);
      // Stronger assertion when available: assert actual rendered dimensions
      if (chartEl.offsetWidth !== 0 && chartEl.offsetHeight !== 0) {
        expect(chartEl.offsetWidth).toBe(600);
        expect(chartEl.offsetHeight).toBe(200);
      }
    });
```

*Verification:*
```
Action: npm test -- --testPathPattern="welder/\[id\]/page"
Expected: Pass
Pass criteria:
  [ ] trend-chart element found
  [ ] style attribute contains width 600 and height 200
  [ ] When offsetWidth/offsetHeight non-zero, assert 600×200
If it fails: Ensure data-testid or id present; check inline style format; jsdom may not compute layout — style assertion suffices
```

*Estimate:* 0.25h  

---

**Step 4.5 — Unit test for getApiBase**

*What:* Add tests for getApiBase. **Two test files** — Node (api-base.node.test.ts) and jsdom (api-base.jsdom.test.ts). Node tests return "". jsdom tests exercise the basePath branch by mutating process.env.NEXT_PUBLIC_BASE_PATH. **Note:** Next.js inlines NEXT_PUBLIC_* at build time; the jsdom test mutates process.env and exercises the logic path in Jest, but **does not verify build-time inlining**. For production basePath verification: Pre-Flight curl with basePath prefix.

*File:* `my-app/src/__tests__/lib/api-base.node.test.ts` (create), `my-app/src/__tests__/lib/api-base.jsdom.test.ts` (create)

*Depends on:* Step 3.3

*Code for api-base.node.test.ts:*
```typescript
/** @jest-environment node */

import { getApiBase } from "@/lib/api-base";

describe("getApiBase (Node)", () => {
  it("returns empty string when run in Node (no window)", () => {
    expect(typeof window).toBe("undefined");
    expect(getApiBase()).toBe("");
  });
});
```

*Code for api-base.jsdom.test.ts:*
```typescript
/** @jest-environment jsdom */

import { getApiBase } from "@/lib/api-base";

describe("getApiBase (jsdom)", () => {
  const origEnv = process.env;

  afterEach(() => {
    process.env = { ...origEnv };
  });

  it("returns base path when NEXT_PUBLIC_BASE_PATH set", () => {
    (process.env as { NEXT_PUBLIC_BASE_PATH?: string }).NEXT_PUBLIC_BASE_PATH = "/weldingsense";
    expect(getApiBase()).toBe("/weldingsense");
  });

  it("strips trailing slash when base path set", () => {
    (process.env as { NEXT_PUBLIC_BASE_PATH?: string }).NEXT_PUBLIC_BASE_PATH = "/weldingsense/";
    expect(getApiBase()).toBe("/weldingsense");
  });

  it("returns empty string when NEXT_PUBLIC_BASE_PATH unset", () => {
    delete (process.env as { NEXT_PUBLIC_BASE_PATH?: string }).NEXT_PUBLIC_BASE_PATH;
    expect(getApiBase()).toBe("");
  });
});
```

*Why:* In Node, getApiBase always returns "" because `typeof window === "undefined"`. The basePath branch is never executed. A separate jsdom test file ensures the env path is exercised. **Pre-Flight curl still required for production basePath verification** — test does not validate build-time inlining.

*Verification:*
```
Action: npm test -- --testPathPattern="api-base"
Expected: All api-base tests pass (Node + jsdom)
Pass criteria:
  [ ] api-base.node.test: getApiBase returns "" in Node
  [ ] api-base.jsdom.test: basePath branches return correct values
If it fails: Ensure jest.config supports per-file testEnvironment; check jsdom installed
```

*Estimate:* 0.5h  

---

**Step 4.6 — API route tests with @jest-environment node**

*What:* Create API route test. Use `/** @jest-environment node */`. Assert PDF header, content, 400 cases, 411 on chunked, 413 on oversized body, welder.name object. **Invalid Content-Length (non-numeric) → 400.** **Use smaller payloads for 413 test (e.g. 5MB+1KB pad) to reduce CI OOM risk.** **Skip 413 when (CI=true OR CI=1) AND CI_LOW_MEM=1** — GitHub Actions, GitLab CI, and many systems set CI=1; both formats must trigger skip.

*File:* `my-app/src/__tests__/api/welder-report-pdf.test.ts` (create)

*Depends on:* Step 2.1

*Code:*
```typescript
/** @jest-environment node */

import { POST } from "@/app/api/welder-report-pdf/route";

const VALID = {
  welder: { name: "Mike Chen" },
  score: { total: 75, rules: [] },
  feedback: {
    summary: "Good work",
    feedback_items: [{ message: "Test", severity: "info", suggestion: null }],
  },
};

const skip413 =
  process.env.CI_LOW_MEM === "1" &&
  (process.env.CI === "true" || process.env.CI === "1");

describe("POST /api/welder-report-pdf", () => {
  it("returns PDF with valid header and content", async () => {
    const req = new Request("http://localhost/api/welder-report-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(VALID),
    });
    const res = await POST(req);
    expect(res.status).toBe(200);
    expect(res.headers.get("Content-Type")).toBe("application/pdf");
    const buf = Buffer.from(await res.arrayBuffer());
    expect(buf.slice(0, 5).toString("utf8")).toBe("%PDF-");
    const str = buf.toString("utf8");
    expect(str).toContain("Mike Chen");
    expect(str).toContain("75");
    expect(str).toContain("Good work");
  });

  it("returns 400 when welder missing", async () => {
    const req = new Request("http://localhost/api/welder-report-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ score: VALID.score, feedback: VALID.feedback }),
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
    const json = await res.json();
    expect(json.error).toMatch(/welder|missing|invalid/i);
  });

  it("returns 400 when score.total is string", async () => {
    const req = new Request("http://localhost/api/welder-report-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        welder: VALID.welder,
        score: { total: "75", rules: [] },
        feedback: VALID.feedback,
      }),
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
    const json = await res.json();
    expect(json.error).toMatch(/score\.total|number/i);
  });

  it("returns 400 when chartDataUrl exceeds max length", async () => {
    const big = "A".repeat(2 * 1024 * 1024 + 1);
    const req = new Request("http://localhost/api/welder-report-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...VALID, chartDataUrl: `data:image/png;base64,${big}` }),
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
    const json = await res.json();
    expect(json.error).toMatch(/chartDataUrl|exceeds/i);
  });

  it("accepts welder.name as object and coerces to Unknown", async () => {
    const req = new Request("http://localhost/api/welder-report-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...VALID,
        welder: { name: { first: "Mike" } },
      }),
    });
    const res = await POST(req);
    expect(res.status).toBe(200);
    const buf = Buffer.from(await res.arrayBuffer());
    const str = buf.toString("utf8");
    expect(str).not.toContain("[object Object]");
    expect(str).toContain("Unknown");
  });

  it("returns 400 when Content-Length is invalid (non-numeric)", async () => {
    const req = new Request("http://localhost/api/welder-report-pdf", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": "five",
      },
      body: JSON.stringify(VALID),
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
    const json = await res.json();
    expect(json.error).toMatch(/Content-Length|invalid/i);
  });

  it("returns 411 when Transfer-Encoding chunked without Content-Length", async () => {
    const req = new Request("http://localhost/api/welder-report-pdf", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Transfer-Encoding": "chunked",
      },
      body: JSON.stringify(VALID),
    });
    const res = await POST(req);
    expect(res.status).toBe(411);
    const json = await res.json();
    expect(json.error).toMatch(/chunked|Content-Length/i);
  });

  (skip413 ? it.skip : it)("returns 413 when body exceeds max size", async () => {
    const PAD_SIZE = 5 * 1024 * 1024 + 1024;
    const pad = "x".repeat(PAD_SIZE);
    const payload = JSON.stringify({ ...VALID, pad });
    const req = new Request("http://localhost/api/welder-report-pdf", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": String(Buffer.byteLength(payload)),
      },
      body: payload,
    });
    const res = await POST(req);
    expect(res.status).toBe(413);
  });

  it("toWelderName invariant: null/undefined/object never produce [object Object] or undefined in PDF", async () => {
    const cases = [
      { name: null },
      { name: undefined },
      { name: [] },
    ];
    for (const welderInput of cases) {
      const req = new Request("http://localhost/api/welder-report-pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          welder: welderInput,
          score: VALID.score,
          feedback: VALID.feedback,
        }),
      });
      const res = await POST(req);
      expect(res.status).toBe(200);
      const buf = Buffer.from(await res.arrayBuffer());
      const str = buf.toString("utf8");
      expect(str).not.toContain("[object Object]");
      expect(str).not.toContain("undefined");
    }
  });
});
```

*Why this approach:* .cursorrules require automated tests. Node env for renderToBuffer. 411 test validates chunked rejection (may not run in some runtimes; see Known Issues). welder.name object test validates toWelderName. Invalid Content-Length returns 400. 413 uses 5MB+ pad; if CI OOMs, set CI_LOW_MEM=1 **and** CI=true (or CI=1) to skip 413 test. toWelderName invariant test ensures filename/PDF never leak object stringification.

*Verification:*
```
Setup: cd my-app
Action: npm test -- --testPathPattern="welder-report-pdf"
Expected: All tests pass
Pass criteria:
  [ ] @jest-environment node
  [ ] PDF header, content assertions pass
  [ ] 400 (welder missing, score.total string, chartDataUrl oversized, invalid Content-Length), 411, 413, welder.name object, toWelderName invariant tests pass
If it fails: Ensure Node env; reduce PAD_SIZE if OOM; moduleNameMapper @
```

*Estimate:* 0.75h  

---

**Step 4.7 — Keep Email Report alert test**

*What:* Email Report remains stub; keep its alert test.

*File:* `my-app/src/__tests__/app/seagull/welder/[id]/page.test.tsx` (no change)

*Verification:*
```
Action: npm test -- --testPathPattern="welder/\[id\]/page"
Expected: Email Report test passes
Pass criteria:
  [ ] Email Report alert still asserted
```

*Estimate:* 0h  

---

## Risk Heatmap

| Phase.Step | Risk Description | Probability | Impact | Early Warning | Mitigation |
|------------|------------------|-------------|--------|---------------|------------|
| 1.2 | @react-pdf/renderer incompatible with Next 16/React 19 | Low | High | Build/runtime error | Step 1.3 smoke; pin versions |
| 2.1 | Oversized body OOM | Low | High | Server hang/OOM | Content-Length check; reject chunked; 413; Step 4.6 |
| 2.1 | Chunked encoding bypasses size limit | Low | High | OOM | Reject 411 when chunked without Content-Length (Step 2.1) |
| 2.1 | Client lies about Content-Length; server OOM | Low | High | request.json() buffers full body | Document limitation; recommend reverse-proxy body limit (nginx/Cloudflare); Pre-Flight for production |
| 2.1 | welder.name object → [object Object] | Low | Med | Bad PDF/filename | toWelderName; Step 1.3, 4.6 |
| 2.1 | chartDataUrl type coercion bypasses validation | Low | Med | 500 on render | Explicit typeof; reject non-PNG |
| 2.3 | grep heuristic misses new bad values | Low | Med | Regression ships | Step 4.6 API tests; consider pdf-parse (Known Issues) |
| 3.2 | Orphaned toPng promise → unhandledrejection | Med | Med | Error overlay | .catch(() => {}) on toPng (Step 3.2) |
| 3.3 | basePath deployment → 404 | Med | High | Download 404 in prod | getApiBase; NEXT_PUBLIC_BASE_PATH; Pre-Flight curl |
| 3.3 | html-to-image fails on Recharts | Med | High | chartDataUrl null | try/catch; fallback; Step 4.3 |
| 4.3 | toPng mock bleed between tests | Low | Med | Flaky chart fallback test | try/finally restore (Step 4.3) |
| 4.5 | getApiBase basePath branch untested | Low | Med | basePath fails despite green | jsdom test (Step 4.5); Pre-Flight curl with basePath |
| 4.6 | API test OOM on low-memory CI | Low | Med | Flaky CI | CI_LOW_MEM=1 + (CI=true or CI=1); document 2GB min RAM; 413 exercised in nightly/staging |

---

## Pre-Flight Checklist

### Phase 1 Prerequisites:
- [ ] Node 18+ — `node -v` — Upgrade Node
- [ ] my-app builds — `cd my-app && npm run build` — Fix build errors
- [ ] No existing components/pdf — `ls my-app/src/components/pdf 2>/dev/null` — Remove or merge
- [ ] Prototype pdf-route.mts exists — `test -f my-app/prototype/pdf-route.mts` — Create/restore
- [ ] Use npm ci after install — `cd my-app && npm ci` — Prevents lockfile drift
- [ ] package-lock.json committed — `git diff --quiet my-app/package-lock.json` — Must pass before Phase 2; fail build if uncommitted
- [ ] Automated lockfile check — Add to CI or pre-Phase-2 script: `git diff --quiet my-app/package-lock.json || { echo "FAIL: package-lock.json has uncommitted changes"; exit 1; }`

### Phase 2 Prerequisites:
- [ ] WelderReportPDF exists and compiles — `npx tsc --noEmit` — Fix component
- [ ] **Step 1.3 smoke passed** — `cd my-app && npx tsx prototype/pdf-route.mts` exit 0 — **Do not start Phase 2 until this passes**
- [ ] @react-pdf/renderer installed — `grep @react-pdf my-app/package.json` — npm install
- [ ] @ maps to src — Check tsconfig — Verify paths
- [ ] **Dev server running** — `curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/health 2>/dev/null || true` — Start with `npm run dev` before curl verification. If no health endpoint: `curl -s -o /dev/null -w '%{http_code}' http://localhost:3000` — Expect 200 or 404; connection refused means server not running
- [ ] **Positive PDF route health check** — `curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:3000/api/welder-report-pdf -H "Content-Type: application/json" -d '{"welder":{"name":"X"},"score":{"total":75,"rules":[]},"feedback":{"summary":"","feedback_items":[{"message":"X","severity":"info"}]}}'` — Expect 200; 404 means route missing/wrong path
- [ ] **basePath (if configured):** curl with basePath prefix — `curl -X POST http://localhost:3000/app/api/welder-report-pdf ...` when next.config basePath is /app — Catch getApiBase bugs before deploy; add to CI/release checklist

### Phase 3 Prerequisites:
- [ ] API route returns PDF on valid POST — curl from 2.1 — Fix route
- [ ] Welder page has report, score, displayName — Code review — Ensure state populated
- [ ] html-to-image installed — `grep html-to-image my-app/package.json` — npm install
- [ ] LineChart on page — Code review — Step 3.1 adds wrapper
- [ ] **basePath (if configured):** curl with basePath prefix — `curl -X POST http://localhost:3000/app/api/welder-report-pdf ...` when next.config basePath is /app — Catch getApiBase bugs before deploy

### Phase 4 Prerequisites:
- [ ] handleDownloadPDF wired — Manual click works — Wire handler
- [ ] Jest supports per-file testEnvironment — `/** @jest-environment node */` works — Check jest docs
- [ ] basePath (optional): If next.config has basePath, set NEXT_PUBLIC_BASE_PATH at build — `echo $NEXT_PUBLIC_BASE_PATH` — Match basePath
- [ ] CI memory: 2GB+ recommended — Reduce Step 4.6 PAD_SIZE if OOM
- [ ] CI config: For 413 skip, set `CI=true` (or `CI=1`) **and** `CI_LOW_MEM=1` in CI environment — GitHub Actions uses CI=true; GitLab uses CI; some use CI=1

---

## Success Criteria

| # | Condition | How to Verify | Priority |
|---|-----------|---------------|----------|
| 1 | User clicks "Download PDF" and receives PDF | Click; file downloads; open PDF | P0 |
| 2 | PDF contains welder name, date, total score | Step 4.6 automated test | P0 |
| 3 | PDF contains AI coach summary | Step 4.6 | P0 |
| 4 | PDF contains up to 3 feedback items with severity | Inspect PDF | P0 |
| 5 | PDF contains "Score Trend" when chartDataUrl provided | Capture works; PDF has chart | P0 |
| 6 | PDF omits chart when chartDataUrl null | Step 4.3; manual smoke (remove trend-chart) | P0 |
| 7 | PDF footer "WarpSense Quality Intelligence" and "CONFIDENTIAL" | Inspect PDF | P0 |
| 8 | Filename {welder.name}-warp-report.pdf (sanitized, max 64) | Check download | P0 |
| 9 | trend-chart element exists with 600×200 | Step 4.4 automated test | P0 |
| 10 | API returns 400 on invalid Content-Length, 411 on chunked, 413 on oversized | Steps 2.2, 2.3, 4.6 | P0 |
| 11 | Button disabled during generation | Step 4.2 automated test | P0 |
| 12 | Unit test asserts fetch with correct payload | Step 4.1 | P0 |
| 13 | chartDataUrl null when capture fails | Step 4.3 | P0 |
| 14 | welder.name object does not produce [object Object] | Step 1.3, 4.6 | P0 |
| 15 | getApiBase basePath branch exercised (jsdom test) | Step 4.5; Pre-Flight curl for prod | P1 |
| 16 | toWelderName invariant: always string before sanitizeDownloadFilename | Step 4.6 invariant test | P0 |
| 17 | Pre-Flight positive health check passes for PDF route | curl POST returns 200 | P0 |

---

## Known Issues & Limitations

- **Chart capture best-effort:** html-to-image may fail on Recharts in some browsers. When it fails, chartDataUrl is null; PDF omits chart. Step 4.3 tests fallback. No "Chart unavailable" UX; user gets PDF without chart.
- **basePath:** If next.config has basePath, set NEXT_PUBLIC_BASE_PATH at build. getApiBase() used for fetch. Step 4.5 tests getApiBase logic in Jest; **Next.js inlines NEXT_PUBLIC_* at build time — the jsdom test mutates process.env and exercises the logic path but does not verify build-time inlining.** Pre-Flight curl with basePath prefix before deploy is required for production verification.
- **npm ci:** Use for installs to avoid lockfile drift. Commit package-lock.json. Automated check (`git diff --quiet my-app/package-lock.json`) should fail build if lockfile has uncommitted changes.
- **Content-Length trust assumption:** Body size check only works when client sends Content-Length. **Server does not enforce read limit at stream level** — `request.json()` buffers the full body. A client that lies (sends Content-Length: 5000 but streams 20MB) can cause OOM. **Recommendation:** Configure reverse-proxy (nginx, Cloudflare) body limit for production. Invalid (non-numeric) Content-Length returns 400. Chunked requests are rejected (411) to prevent OOM. 5MB limit applies only when Content-Length present. When deploying without nginx (e.g. serverless), body limit risk remains.
- **411 chunked test:** The Request API with body typically adds Content-Length, stripping chunked. curl -d also typically adds Content-Length. The 411 branch may be dead code in production; the defense exists but standard fetch/Request/curl may never trigger it. Document as defensive-only; integration test with raw socket would be needed to verify chunked rejection.
- **welder.name:** Validated/coerced via toWelderName. Non-string produces "Unknown" in PDF and filename. toWelderName always returns string.
- **CI OOM:** Step 4.6 413 test allocates ~5MB. Minimum 2GB RAM recommended. If CI OOMs: set `CI_LOW_MEM=1` **and** `CI=true` or `CI=1`. **CI env format:** GitHub Actions sets CI=true; GitLab CI and others may set CI=1. Both must trigger skip — plan uses `(process.env.CI === 'true' || process.env.CI === '1') && process.env.CI_LOW_MEM === '1'`. Document in CI config: `CI: true` (or `CI: "1"`) and `CI_LOW_MEM: "1"` for low-memory runs. **When 413 is exercised:** Run 413 test in nightly or staging with sufficient RAM; low-memory CI skips it.
- **Step 2.3 grep validation:** Grep for "Unknown" and "[object Object]" is heuristic. New bad values (e.g. "undefined", "null") could slip through. Step 4.6 API tests cover validation paths. Consider pdf-parse for programmatic PDF content assertion (optional enhancement).
- **sanitizeText:** Defined in `my-app/src/components/pdf/WelderReportPDF.tsx`. Strips control chars, zero-width, RTL-override.
- **Step 1.3 PDF text verification:** `buffer.toString("utf8").includes("Mike Chen")` assumes @react-pdf/renderer emits plain UTF-8. If react-pdf switches to compressed streams or hex-encoded text, this heuristic fails. Use pdf-parse or visual verification if Step 1.3 fails after dependency update.
