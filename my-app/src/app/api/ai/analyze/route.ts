/**
 * POST /api/ai/analyze — proxy to backend AI analyze.
 * Body: { query: string, offline?: boolean }
 */

import { NextResponse } from "next/server";
import { getServerBackendBaseUrl } from "@/lib/server-backend-base-url";

const API_BASE = getServerBackendBaseUrl();

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { query, offline = false } = body;
    if (!query || typeof query !== "string" || !query.trim()) {
      return NextResponse.json(
        { detail: "query is required" },
        { status: 400 }
      );
    }
    const res = await fetch(`${API_BASE}/api/ai/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query.trim(), offline }),
    });
    const data = await res.json();
    if (!res.ok) {
      return NextResponse.json(data, { status: res.status });
    }
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json(
      {
        source: "error",
        error: "Could not reach backend. Make sure the server is running.",
        function_calls: [],
      },
      { status: 200 }
    );
  }
}
