/**
 * GET /api/ai/health — proxy to backend AI health.
 */

import { NextResponse } from "next/server";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const res = await fetch(`${API_BASE}/api/ai/health`);
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { cactus: "error", gemini: "error", model_loaded: false },
      { status: 200 }
    );
  }
}
