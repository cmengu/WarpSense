/**
 * Chart capture for PDF report.
 *
 * Uses html-to-image toPng to capture a DOM element (e.g. trend LineChart)
 * to base64 PNG. Option A per plan: client-side capture, pre-render before POST.
 */

import { toPng } from "html-to-image";

const CAPTURE_TIMEOUT_MS = 10_000;

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T | null> {
  let timeoutId: ReturnType<typeof setTimeout>;
  const timeout = new Promise<null>((_, reject) => {
    timeoutId = setTimeout(() => reject(new Error("Capture timeout")), ms);
  });
  const raced = Promise.race([promise, timeout]).finally(() =>
    clearTimeout(timeoutId)
  );
  return raced;
}

/**
 * Capture a DOM element to base64 PNG.
 * Returns null if element not found, capture fails, or times out.
 * When timeout wins, the toPng promise continues — attach .catch to prevent unhandledrejection.
 */
export async function captureChartToBase64(
  elementId: string
): Promise<string | null> {
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
