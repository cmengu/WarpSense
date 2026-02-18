/**
 * Tests for WelderReport page — 10 welders with historical scores.
 *
 * Validates:
 *   - Renders score header, AI summary, heatmaps, feedback, chart when data loads
 *   - Error state with back link when fetch fails
 *   - Back nav link to /seagull
 *   - Fetches primary session, expert (sess_expert-benchmark_005), score, historical scores
 */

import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import WelderReportPage from "@/app/seagull/welder/[id]/page";

const mockFetchSession = jest.fn();
const mockFetchScore = jest.fn();

jest.mock("html-to-image", () => ({
  toPng: jest.fn().mockResolvedValue("data:image/png;base64,fake"),
}));

jest.mock("@/lib/api", () => ({
  fetchSession: (...args: unknown[]) => mockFetchSession(...args),
  fetchScore: (...args: unknown[]) => mockFetchScore(...args),
}));

const mockSession = {
  session_id: "sess_mike-chen_005",
  operator_id: "mike-chen",
  start_time: "2026-02-07T10:00:00Z",
  weld_type: "butt_joint",
  thermal_sample_interval_ms: 100,
  thermal_directions: ["center", "north", "south", "east", "west"],
  thermal_distance_interval_mm: 10.0,
  sensor_sample_rate_hz: 100,
  frames: [
    {
      timestamp_ms: 0,
      volts: 22,
      amps: 150,
      angle_degrees: 45,
      thermal_snapshots: [
        {
          distance_mm: 10,
          readings: [{ direction: "center" as const, temp_celsius: 400 }],
        },
      ],
      has_thermal_data: true,
      optional_sensors: null,
      heat_dissipation_rate_celsius_per_sec: null,
    },
  ],
  status: "complete" as const,
  frame_count: 1,
  expected_frame_count: 1,
  last_successful_frame_index: 0,
  validation_errors: [],
  completed_at: "2026-02-07T10:00:01Z",
};

const mockScore = {
  total: 75,
  rules: [
    {
      rule_id: "amps_stability",
      threshold: 3,
      passed: false,
      actual_value: 5.2,
    },
    {
      rule_id: "angle_consistency",
      threshold: 5,
      passed: true,
      actual_value: 3.1,
    },
  ],
};

describe("WelderReportPage", () => {
  beforeEach(() => {
    mockFetchSession.mockResolvedValue(mockSession);
    mockFetchScore.mockResolvedValue(mockScore);
  });

  it("renders report with score, AI summary, heatmaps, feedback when data loads", async () => {
    render(<WelderReportPage params={{ id: "mike-chen" }} />);

    await waitFor(() => {
      expect(screen.getByText(/75\/100/)).toBeInTheDocument();
    });

    expect(screen.getByText(/Mike Chen — Weekly Report/)).toBeInTheDocument();
    expect(screen.getByText(/🤖 AI Analysis:/)).toBeInTheDocument();
    expect(screen.getByText(/Thermal Comparison/)).toBeInTheDocument();
    expect(screen.getByText(/Detailed Feedback/)).toBeInTheDocument();
    expect(screen.getByText(/Progress Over Time/)).toBeInTheDocument();
  });

  it("shows error state with back link when fetch fails", async () => {
    mockFetchSession.mockRejectedValueOnce(new Error("Network error"));

    render(<WelderReportPage params={{ id: "mike-chen" }} />);

    await waitFor(() => {
      expect(screen.getByText(/⚠️ Error/)).toBeInTheDocument();
    });

    const backLink = screen.getByRole("link", {
      name: /← Back to Team Dashboard/i,
    });
    expect(backLink).toBeInTheDocument();
    expect(backLink).toHaveAttribute("href", "/seagull");
  });

  it("fetches primary session, expert (sess_expert-benchmark_005), score, and historical scores", async () => {
    render(<WelderReportPage params={{ id: "mike-chen" }} />);

    await waitFor(() => {
      expect(screen.getByText(/75\/100/)).toBeInTheDocument();
    });

    expect(mockFetchSession).toHaveBeenCalledWith("sess_mike-chen_005", {
      limit: 2000,
    });
    expect(mockFetchSession).toHaveBeenCalledWith(
      "sess_expert-benchmark_005",
      { limit: 2000 }
    );
    expect(mockFetchScore).toHaveBeenCalledWith("sess_mike-chen_005");
    expect(mockFetchScore).toHaveBeenCalledWith("sess_mike-chen_001");
    expect(mockFetchScore).toHaveBeenCalledWith("sess_mike-chen_002");
  });

  it("maps expert-benchmark id to sess_expert-benchmark_005", async () => {
    render(<WelderReportPage params={{ id: "expert-benchmark" }} />);

    await waitFor(() => {
      expect(
        screen.getByText(/Expert Benchmark — Weekly Report/)
      ).toBeInTheDocument();
    });

    expect(mockFetchSession).toHaveBeenCalledWith(
      "sess_expert-benchmark_005",
      { limit: 2000 }
    );
  });

  it("shows Back to Team Dashboard link when report loads", async () => {
    render(<WelderReportPage params={{ id: "mike-chen" }} />);

    await waitFor(() => {
      expect(screen.getByText(/75\/100/)).toBeInTheDocument();
    });

    const backLink = screen.getByRole("link", {
      name: /← Back to Team Dashboard/i,
    });
    expect(backLink).toHaveAttribute("href", "/seagull");
  });

  describe("Export stubs", () => {
    it("Email Report button shows alert when clicked", async () => {
      const alertSpy = jest.spyOn(window, "alert").mockImplementation(() => {});

      render(<WelderReportPage params={{ id: "mike-chen" }} />);
      await waitFor(() => {
        expect(screen.getByText(/75\/100/)).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Email Report/i }));
      expect(alertSpy).toHaveBeenCalledWith("Email report — coming soon");

      alertSpy.mockRestore();
    });
  });

  describe("Download PDF", () => {
    let originalFetch: typeof global.fetch;

    beforeEach(() => {
      originalFetch = global.fetch;
    });

    afterEach(() => {
      global.fetch = originalFetch;
    });

    it("POSTs to API with correct payload", async () => {
      const mockBlob = new Blob(["pdf"], { type: "application/pdf" });
      const mockFetch = jest.fn().mockResolvedValue({
        ok: true,
        blob: () => Promise.resolve(mockBlob),
      });
      global.fetch = mockFetch as typeof fetch;

      render(<WelderReportPage params={{ id: "mike-chen" }} />);
      await waitFor(() =>
        expect(screen.getByText(/75\/100/)).toBeInTheDocument()
      );

      fireEvent.click(screen.getByRole("button", { name: /Download PDF/i }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining("/api/welder-report-pdf"),
          expect.objectContaining({
            method: "POST",
            headers: { "Content-Type": "application/json" },
          })
        );
      });

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.welder).toEqual({ name: "Mike Chen" });
      expect(body.score.total).toBe(75);
      expect(body.feedback).toBeDefined();
    });

    it("Download PDF button is disabled during generation", async () => {
      let resolveFetch: (v: {
        ok: boolean;
        blob: () => Promise<Blob>;
      }) => void;
      const fetchPromise = new Promise<{
        ok: boolean;
        blob: () => Promise<Blob>;
      }>((r) => {
        resolveFetch = r;
      });
      const mockFetch = jest.fn().mockReturnValue(fetchPromise);
      global.fetch = mockFetch as typeof fetch;

      try {
        render(<WelderReportPage params={{ id: "mike-chen" }} />);
        await waitFor(() =>
          expect(screen.getByText(/75\/100/)).toBeInTheDocument()
        );
        const btn = screen.getByRole("button", { name: /Download PDF/i });
        fireEvent.click(btn);
        await waitFor(() => expect(btn).toBeDisabled());
        resolveFetch!({ ok: true, blob: () => Promise.resolve(new Blob()) });
      } finally {
        global.fetch = originalFetch;
      }
    });

    it("sends chartDataUrl null when chart capture fails", async () => {
      const { toPng } = require("html-to-image");
      (toPng as jest.Mock).mockResolvedValue(null);

      const mockBlob = new Blob(["pdf"], { type: "application/pdf" });
      const mockFetch = jest.fn().mockResolvedValue({
        ok: true,
        blob: () => Promise.resolve(mockBlob),
      });
      global.fetch = mockFetch as typeof fetch;

      try {
        render(<WelderReportPage params={{ id: "mike-chen" }} />);
        await waitFor(() =>
          expect(screen.getByText(/75\/100/)).toBeInTheDocument()
        );
        fireEvent.click(screen.getByRole("button", { name: /Download PDF/i }));
        await waitFor(() => expect(mockFetch).toHaveBeenCalled());

        const body = JSON.parse(mockFetch.mock.calls[0][1].body);
        expect(body.chartDataUrl).toBeNull();
      } finally {
        global.fetch = originalFetch;
        (toPng as jest.Mock).mockResolvedValue("data:image/png;base64,fake");
      }
    });

    it("renders trend-chart wrapper with 600×200 for PDF capture", async () => {
      render(<WelderReportPage params={{ id: "mike-chen" }} />);
      await waitFor(() =>
        expect(screen.getByText(/75\/100/)).toBeInTheDocument()
      );

      const chartEl =
        document.getElementById("trend-chart") ??
        screen.getByTestId("trend-chart");
      expect(chartEl).toBeInTheDocument();
      const style = chartEl.getAttribute("style") ?? "";
      expect(style).toMatch(/width.*600|600.*width/i);
      expect(style).toMatch(/height.*200|200.*height/i);
      if (chartEl.offsetWidth !== 0 && chartEl.offsetHeight !== 0) {
        expect(chartEl.offsetWidth).toBe(600);
        expect(chartEl.offsetHeight).toBe(200);
      }
    });
  });
});
