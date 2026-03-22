/**
 * GET /api/ai/health — proxy to backend AI health.
 */

import { NextResponse } from "next/server";
import { getServerBackendBaseUrl } from "@/lib/server-backend-base-url";

const API_BASE = getServerBackendBaseUrl();

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
