/**
 * POST /api/warp/sessions/[sessionId]/analyse
 * Pipes FastAPI SSE stream to client — zero buffering.
 *
 * MUST use new Response(upstream.body). NextResponse.json() buffers the
 * entire stream before sending — this kills the live-progress UX.
 * Client uses fetch() + ReadableStream. Never EventSource (POST route).
 * Next.js 16: params is a Promise — await before use.
 */
import { NextResponse } from "next/server";
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
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
