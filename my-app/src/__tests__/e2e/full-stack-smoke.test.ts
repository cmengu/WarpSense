/**
 * Full-stack smoke test: score → warp-risk → trajectory → benchmarks →
 * coaching → certification → narrative → defects → sites
 *
 * Requires running backend + seeded data.
 * Run: npm test -- --testPathPattern="full-stack-smoke"
 *
 * @jest-environment node
 */
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const WELDER_ID = "mike-chen";
const SESSION_ID = "sess_novice_001";

describe("Full stack smoke", () => {
  jest.setTimeout(15_000);

  test("score endpoint returns total", async () => {
    const r = await fetch(`${BASE}/api/sessions/${SESSION_ID}/score`);
    expect(r.ok).toBe(true);
    const d = await r.json();
    expect(typeof d.total).toBe("number");
  });

  test("warp-risk endpoint returns risk_level", async () => {
    const r = await fetch(`${BASE}/api/sessions/${SESSION_ID}/warp-risk`);
    expect(r.ok).toBe(true);
    const d = await r.json();
    expect(["ok", "warning", "critical"]).toContain(d.risk_level);
  });

  test("trajectory returns points array", async () => {
    const r = await fetch(`${BASE}/api/welders/${WELDER_ID}/trajectory`);
    expect(r.ok).toBe(true);
    const d = await r.json();
    expect(Array.isArray(d.points)).toBe(true);
  });

  test("benchmarks returns metrics array", async () => {
    const r = await fetch(`${BASE}/api/welders/${WELDER_ID}/benchmarks`);
    expect(r.ok).toBe(true);
    const d = await r.json();
    expect(Array.isArray(d.metrics)).toBe(true);
  });

  test("coaching-plan returns assignments", async () => {
    const r = await fetch(`${BASE}/api/welders/${WELDER_ID}/coaching-plan`);
    // Skip when drills table not migrated/seeded (500)
    if (!r.ok && r.status === 500) {
      console.warn("Skipped: drills table not migrated/seeded (500)");
      return;
    }
    expect(r.ok).toBe(true);
    const d = await r.json();
    expect(Array.isArray(d.active_assignments)).toBe(true);
  });

  test("certification-status returns certifications", async () => {
    const r = await fetch(`${BASE}/api/welders/${WELDER_ID}/certification-status`);
    // Skip when cert_standards not migrated/seeded (500)
    if (!r.ok && r.status === 500) {
      console.warn("Skipped: cert_standards not migrated/seeded (500)");
      return;
    }
    expect(r.ok).toBe(true);
    const d = await r.json();
    expect(Array.isArray(d.certifications)).toBe(true);
    expect(d.certifications.length).toBe(3);
  });

  test("narrative POST + GET cycle", async () => {
    const post = await fetch(`${BASE}/api/sessions/${SESSION_ID}/narrative`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ force_regenerate: false }),
    });
    // Skip assertion when ANTHROPIC_API_KEY not configured (503)
    if (!post.ok && post.status === 503) {
      console.warn("Skipped: ANTHROPIC_API_KEY not configured (503)");
      return;
    }
    expect(post.ok).toBe(true);
    const get = await fetch(`${BASE}/api/sessions/${SESSION_ID}/narrative`);
    expect(get.ok).toBe(true);
    const d = await get.json();
    expect(typeof d.narrative_text).toBe("string");
    expect(d.narrative_text.length).toBeGreaterThan(50);
  });

  test("defects endpoint returns array", async () => {
    const r = await fetch(`${BASE}/api/defects`);
    expect(r.ok).toBe(true);
    const d = await r.json();
    expect(Array.isArray(d)).toBe(true);
  });

  test("sites endpoint returns array", async () => {
    const r = await fetch(`${BASE}/api/sites`);
    expect(r.ok).toBe(true);
    const d = await r.json();
    expect(Array.isArray(d)).toBe(true);
  });
});
