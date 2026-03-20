"use client";
/** /analysis — WarpSense analysis surface. Full UI in Phase UI-7. */
export default function AnalysisPage() {
  return (
    <div style={{ minHeight: "100vh", background: "var(--warp-bg)",
      fontFamily: "var(--font-warp-mono), monospace", color: "var(--warp-text)",
      display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center" }}>
        <p style={{ fontSize: 10, letterSpacing: "0.2em", color: "var(--warp-text-muted)", marginBottom: 8 }}>
          WARPSENSE
        </p>
        <p style={{ fontSize: 14, color: "var(--warp-orange)", letterSpacing: "0.1em" }}>
          ANALYSIS ENGINE — Phase UI-2 scaffold
        </p>
      </div>
    </div>
  );
}
