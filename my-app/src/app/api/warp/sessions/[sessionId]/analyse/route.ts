/**
 * POST /api/warp/sessions/[sessionId]/analyse
 * Same-origin proxy: pipes FastAPI SSE with new Response(upstream.body).
 *
 * Browser UI uses `streamAnalysis()` in warp-api.ts → direct POST to FastAPI instead,
 * to avoid any proxy buffering/timing issues. Keep this route for curl/tests/same-origin tools.
 * Backend is POST-only for analyse — EventSource (GET) does not apply.
 * Next.js 16: params is a Promise — await before use.
 */
import { NextResponse } from "next/server";
import { getServerBackendBaseUrl } from "@/lib/server-backend-base-url";

const API_BASE = getServerBackendBaseUrl();
export const dynamic = "force-dynamic";
// Node.js runtime required — Edge runtime does not support ReadableStream pipe-through.
export const runtime = "nodejs";
export async function POST(
  _request: Request,
  { params }: { params: Promise<{ sessionId: string }> },
): Promise<Response> {
  const { sessionId } = await params;
  try {
    const upstream = await fetch(`${API_BASE}/api/sessions/${sessionId}/analyse`, {
      method: "POST",
      headers: { Accept: "text/event-stream" },
    });
    if (!upstream.ok || !upstream.body) {
      return NextResponse.json({ detail: `Backend ${upstream.status}` }, { status: upstream.status });
    }
    return new Response(upstream.body, {
      status: 200,
      headers: {
        "Content-Type":      "text/event-stream",
        "Cache-Control":     "no-cache",
        "X-Accel-Buffering": "no",
        Connection:          "keep-alive",
      },
    });
  } catch {
    return NextResponse.json({ detail: "Backend unreachable" }, { status: 502 });
  }
}
