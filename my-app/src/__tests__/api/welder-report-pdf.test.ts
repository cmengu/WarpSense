/** @jest-environment node */

import { POST } from "@/app/api/welder-report-pdf/route";

const VALID = {
  welder: { name: "Mike Chen" },
  score: { total: 75, rules: [] },
  feedback: {
    summary: "Good work",
    feedback_items: [
      { message: "Test", severity: "info", suggestion: null },
    ],
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
      body: JSON.stringify({
        ...VALID,
        chartDataUrl: `data:image/png;base64,${big}`,
      }),
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

  (skip413 ? it.skip : it)(
    "returns 413 when body exceeds max size",
    async () => {
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
    }
  );

  it("accepts optional sessionDate, duration, station and renders PDF", async () => {
    const req = new Request("http://localhost/api/welder-report-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...VALID,
        sessionDate: "2/27/2026",
        duration: "4 min 12 sec",
        station: "Station 4",
      }),
    });
    const res = await POST(req);
    expect(res.status).toBe(200);
    const buf = Buffer.from(await res.arrayBuffer());
    const str = buf.toString("utf8");
    expect(str).toContain("2/27/2026");
    expect(str).toContain("4 min 12 sec");
    expect(str).toContain("Station 4");
  });

  it("toWelderName invariant: null/undefined/object never produce [object Object] or undefined in PDF", async () => {
    const cases = [{ name: null }, { name: undefined }, { name: [] }];
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
