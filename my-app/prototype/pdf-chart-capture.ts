/**
 * Prototype: html-to-image capture of Recharts LineChart.
 *
 * Run after: npm install html-to-image
 * Use: Import in a test or add to welder page temporarily.
 *
 * Critical assumption: toPng(element) works on a div containing Recharts SVG.
 * Recharts renders SVG; html-to-image supports SVG → canvas → PNG.
 *
 * ResponsiveContainer uses width="100%" — parent MUST have explicit dimensions
 * or capture may produce wrong size. Wrap in:
 *   <div id="trend-chart" style={{ width: 600, height: 200 }}>
 *
 * Known quirk: toPng can fail if element has filters or external resources.
 * Fallback: return null, PDF omits chart section.
 */
import { toPng } from "html-to-image";

export async function captureChartToBase64(
  elementId: string
): Promise<string | null> {
  const el = document.getElementById(elementId);
  if (!el) return null;
  try {
    const dataUrl = await toPng(el, {
      cacheBust: true,
      pixelRatio: 2, // crisper output for PDF
    });
    return dataUrl;
  } catch {
    return null;
  }
}
