/**
 * Tests for frontend API client (Step 13).
 *
 * Validates:
 *   - URL construction with query parameters
 *   - fetchSession() with pagination, filtering, streaming params
 *   - addFrames() POST with correct body and headers
 *   - Error handling: network failures, non-2xx responses, JSON detail parsing
 *   - fetchDashboardData() backward compatibility
 */

import {
  API_BASE_URL,
  buildUrl,
  fetchDashboardData,
  fetchSession,
  addFrames,
} from "@/lib/api";
import type { AddFramesResponse, FetchSessionParams } from "@/lib/api";
import type { Frame } from "@/types/frame";
import type { Session } from "@/types/session";

// ---------------------------------------------------------------------------
// Mock fetch globally
// ---------------------------------------------------------------------------

const mockFetch = jest.fn() as jest.MockedFunction<typeof fetch>;
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Create a mock Response with JSON body. */
function mockJsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Error",
    json: () => Promise.resolve(body),
    headers: new Headers(),
    redirected: false,
    type: "basic",
    url: "",
    clone: () => mockJsonResponse(body, status),
    body: null,
    bodyUsed: false,
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    blob: () => Promise.resolve(new Blob()),
    formData: () => Promise.resolve(new FormData()),
    text: () => Promise.resolve(JSON.stringify(body)),
    bytes: () => Promise.resolve(new Uint8Array()),
  } as Response;
}

/** Minimal valid session from the API. */
function mockSessionPayload(): Session {
  return {
    session_id: "sess_001",
    operator_id: "op_42",
    start_time: "2026-02-07T10:00:00Z",
    weld_type: "butt_joint",
    thermal_sample_interval_ms: 100,
    thermal_directions: ["center", "north", "south", "east", "west"],
    thermal_distance_interval_mm: 10.0,
    sensor_sample_rate_hz: 100,
    frames: [],
    status: "recording",
    frame_count: 0,
    expected_frame_count: null,
    last_successful_frame_index: null,
    validation_errors: [],
    completed_at: null,
  };
}

/** Minimal frame for addFrames tests. */
function mockFrame(timestamp_ms: number): Frame {
  return {
    timestamp_ms,
    volts: 22.5,
    amps: 150.0,
    angle_degrees: 45.0,
    thermal_snapshots: [],
    has_thermal_data: false,
    optional_sensors: null,
    heat_dissipation_rate_celsius_per_sec: null,
  };
}

// ---------------------------------------------------------------------------
// buildUrl
// ---------------------------------------------------------------------------

describe("buildUrl", () => {
  it("builds a URL with no params", () => {
    const url = buildUrl("/api/sessions/sess_001");
    expect(url).toBe(`${API_BASE_URL}/api/sessions/sess_001`);
  });

  it("appends defined params as query string", () => {
    const url = buildUrl("/api/sessions/sess_001", {
      limit: 500,
      offset: 100,
    });
    const parsed = new URL(url);
    expect(parsed.searchParams.get("limit")).toBe("500");
    expect(parsed.searchParams.get("offset")).toBe("100");
  });

  it("omits undefined params", () => {
    const url = buildUrl("/api/sessions/sess_001", {
      limit: 500,
      offset: undefined,
      include_thermal: undefined,
    });
    const parsed = new URL(url);
    expect(parsed.searchParams.get("limit")).toBe("500");
    expect(parsed.searchParams.has("offset")).toBe(false);
    expect(parsed.searchParams.has("include_thermal")).toBe(false);
  });

  it("handles boolean params", () => {
    const url = buildUrl("/api/sessions/sess_001", {
      include_thermal: false,
      stream: true,
    });
    const parsed = new URL(url);
    expect(parsed.searchParams.get("include_thermal")).toBe("false");
    expect(parsed.searchParams.get("stream")).toBe("true");
  });
});

// ---------------------------------------------------------------------------
// fetchSession
// ---------------------------------------------------------------------------

describe("fetchSession", () => {
  it("calls GET /api/sessions/{sessionId} with default params", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockSessionPayload()));

    const session = await fetchSession("sess_001");

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const calledUrl = mockFetch.mock.calls[0][0] as string;
    expect(calledUrl).toContain("/api/sessions/sess_001");
    expect(session.session_id).toBe("sess_001");
  });

  it("passes pagination params correctly", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockSessionPayload()));

    await fetchSession("sess_001", { limit: 500, offset: 1000 });

    const calledUrl = new URL(mockFetch.mock.calls[0][0] as string);
    expect(calledUrl.searchParams.get("limit")).toBe("500");
    expect(calledUrl.searchParams.get("offset")).toBe("1000");
  });

  it("passes time range params correctly", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockSessionPayload()));

    await fetchSession("sess_001", {
      time_range_start: 5000,
      time_range_end: 10000,
    });

    const calledUrl = new URL(mockFetch.mock.calls[0][0] as string);
    expect(calledUrl.searchParams.get("time_range_start")).toBe("5000");
    expect(calledUrl.searchParams.get("time_range_end")).toBe("10000");
  });

  it("passes include_thermal=false correctly", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockSessionPayload()));

    await fetchSession("sess_001", { include_thermal: false });

    const calledUrl = new URL(mockFetch.mock.calls[0][0] as string);
    expect(calledUrl.searchParams.get("include_thermal")).toBe("false");
  });

  it("passes stream=true correctly", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockSessionPayload()));

    await fetchSession("sess_001", { stream: true });

    const calledUrl = new URL(mockFetch.mock.calls[0][0] as string);
    expect(calledUrl.searchParams.get("stream")).toBe("true");
  });

  it("encodes session ID with special characters", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockSessionPayload()));

    await fetchSession("sess/001 test");

    const calledUrl = mockFetch.mock.calls[0][0] as string;
    expect(calledUrl).toContain("sess%2F001%20test");
  });

  it("omits undefined optional params from URL", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockSessionPayload()));

    await fetchSession("sess_001", { limit: 500 });

    const calledUrl = new URL(mockFetch.mock.calls[0][0] as string);
    expect(calledUrl.searchParams.has("limit")).toBe(true);
    expect(calledUrl.searchParams.has("offset")).toBe(false);
    expect(calledUrl.searchParams.has("include_thermal")).toBe(false);
    expect(calledUrl.searchParams.has("time_range_start")).toBe(false);
    expect(calledUrl.searchParams.has("stream")).toBe(false);
  });

  it("returns typed Session object", async () => {
    const payload = mockSessionPayload();
    mockFetch.mockResolvedValueOnce(mockJsonResponse(payload));

    const session: Session = await fetchSession("sess_001");
    expect(session.session_id).toBe("sess_001");
    expect(session.status).toBe("recording");
    expect(session.frames).toEqual([]);
    expect(session.frame_count).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// addFrames
// ---------------------------------------------------------------------------

describe("addFrames", () => {
  const successResponse: AddFramesResponse = {
    status: "success",
    successful_count: 2,
    failed_frames: [],
    next_expected_timestamp: 20,
    can_resume: true,
  };

  it("sends POST with JSON body and correct headers", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(successResponse));

    const frames = [mockFrame(0), mockFrame(10)];
    await addFrames("sess_001", frames);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [calledUrl, calledInit] = mockFetch.mock.calls[0];
    expect(calledUrl).toContain("/api/sessions/sess_001/frames");
    expect(calledInit).toBeDefined();
    expect(calledInit!.method).toBe("POST");
    expect(calledInit!.headers).toEqual({
      "Content-Type": "application/json",
    });
  });

  it("serializes frames as JSON body", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(successResponse));

    const frames = [mockFrame(0), mockFrame(10)];
    await addFrames("sess_001", frames);

    const body = JSON.parse(mockFetch.mock.calls[0][1]!.body as string);
    expect(body).toHaveLength(2);
    expect(body[0].timestamp_ms).toBe(0);
    expect(body[1].timestamp_ms).toBe(10);
  });

  it("returns typed AddFramesResponse on success", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(successResponse));

    const result = await addFrames("sess_001", [mockFrame(0), mockFrame(10)]);
    expect(result.status).toBe("success");
    expect(result.successful_count).toBe(2);
    expect(result.failed_frames).toEqual([]);
    expect(result.next_expected_timestamp).toBe(20);
    expect(result.can_resume).toBe(true);
  });

  it("returns failure response with frame errors", async () => {
    const failResponse: AddFramesResponse = {
      status: "failed",
      successful_count: 0,
      failed_frames: [
        { index: 0, timestamp_ms: 0, error: "Frames must be sorted" },
      ],
      next_expected_timestamp: null,
      can_resume: false,
    };
    mockFetch.mockResolvedValueOnce(mockJsonResponse(failResponse));

    const result = await addFrames("sess_001", [mockFrame(0)]);
    expect(result.status).toBe("failed");
    expect(result.failed_frames).toHaveLength(1);
    expect(result.failed_frames[0].error).toBe("Frames must be sorted");
    expect(result.can_resume).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Error handling
// ---------------------------------------------------------------------------

describe("Error handling", () => {
  it("throws on network failure with descriptive message", async () => {
    mockFetch.mockRejectedValueOnce(new Error("Connection refused"));

    await expect(fetchSession("sess_001")).rejects.toThrow(
      /Network error.*Connection refused/
    );
  });

  it("throws on 404 with backend detail", async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({ detail: "Session not found" }, 404)
    );

    await expect(fetchSession("nonexistent")).rejects.toThrow(
      /API error 404: Session not found/
    );
  });

  it("throws on 400 with backend detail", async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse(
        { detail: "Session has 30000 frames. Use pagination." },
        400
      )
    );

    await expect(fetchSession("big_session")).rejects.toThrow(
      /API error 400.*Use pagination/
    );
  });

  it("throws on 409 (session locked)", async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse(
        { detail: "Session is locked for concurrent upload" },
        409
      )
    );

    await expect(addFrames("sess_001", [mockFrame(0)])).rejects.toThrow(
      /API error 409.*locked/
    );
  });

  it("throws on 500 with statusText fallback when body is not JSON", async () => {
    const response = {
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.reject(new Error("not JSON")),
      headers: new Headers(),
      redirected: false,
      type: "basic" as ResponseType,
      url: "",
      clone: () => response,
      body: null,
      bodyUsed: false,
      arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
      blob: () => Promise.resolve(new Blob()),
      formData: () => Promise.resolve(new FormData()),
      text: () => Promise.resolve(""),
      bytes: () => Promise.resolve(new Uint8Array()),
    } as Response;
    mockFetch.mockResolvedValueOnce(response);

    await expect(fetchSession("sess_001")).rejects.toThrow(
      /API error 500: Internal Server Error/
    );
  });
});

// ---------------------------------------------------------------------------
// fetchDashboardData — backward compatibility
// ---------------------------------------------------------------------------

describe("fetchDashboardData — backward compatibility", () => {
  it("calls GET /api/dashboard", async () => {
    const mockData = { metrics: [], charts: [] };
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockData));

    const data = await fetchDashboardData();

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const calledUrl = mockFetch.mock.calls[0][0] as string;
    expect(calledUrl).toContain("/api/dashboard");
    expect(data).toEqual(mockData);
  });
});

// ---------------------------------------------------------------------------
// API_BASE_URL
// ---------------------------------------------------------------------------

describe("API_BASE_URL", () => {
  it("defaults to localhost:8000", () => {
    // In test environment, NEXT_PUBLIC_API_URL is not set
    expect(API_BASE_URL).toBe("http://localhost:8000");
  });
});
