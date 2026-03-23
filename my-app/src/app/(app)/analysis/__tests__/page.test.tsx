/**
 * Unit tests for the analysis page state machine.
 *
 * Mocks:
 *  - @/lib/warp-api — all fetch helpers return minimal stubs
 *  - next/dynamic — returns a <div data-testid="welder-trend-chart" />
 *  - @/components/analysis/* — stubs for SessionList, AnalysisTimeline
 */
import type { FC } from "react";
import { render, screen, waitFor, act, fireEvent } from "@testing-library/react";

const mockFetchWarpHealth = jest.fn();
const mockFetchWarpReport = jest.fn();
const mockFetchMockSessions = jest.fn();

jest.mock("@/lib/warp-api", () => ({
  fetchWarpHealth: (...args: unknown[]) => mockFetchWarpHealth(...args),
  fetchWarpReport: (...args: unknown[]) => mockFetchWarpReport(...args),
  fetchMockSessions: (...args: unknown[]) => mockFetchMockSessions(...args),
  fetchWelderTrend: jest.fn().mockResolvedValue([]),
  streamAnalysis: jest.fn(),
}));

jest.mock("next/dynamic", () => {
  return function mockDynamic(
    _loader: () => Promise<{ WelderTrendChart: FC<{ welderId: string }> }>,
  ) {
    return function DynamicWelderTrendChart({ welderId }: { welderId: string }) {
      return <div data-testid="welder-trend-chart" data-welder-id={welderId} />;
    };
  };
});

jest.mock("@/components/analysis/SessionList", () => ({
  SessionList: ({
    onSessionSelect,
    onAnalyseAll,
    selectedSessionId,
    isAnalysing,
  }: {
    onSessionSelect: (s: {
      session_id: string;
      welder_id: string;
      welder_name: string;
    }) => void;
    onAnalyseAll?: () => void;
    selectedSessionId: string | null;
    isAnalysing?: boolean;
  }) => (
    <div
      data-testid="session-list"
      data-selected={selectedSessionId ?? ""}
      data-analysing={String(isAnalysing)}
    >
      <button
        data-testid="select-session-btn"
        type="button"
        onClick={() =>
          onSessionSelect({
            session_id: "mock-session-001",
            welder_id: "expert_aluminium_001",
            welder_name: "Aluminium Expert 01",
          })
        }
      >
        Select Session
      </button>
      {onAnalyseAll && (
        <button data-testid="analyse-all-btn" type="button" onClick={onAnalyseAll}>
          Analyse All
        </button>
      )}
    </div>
  ),
}));

const MOCK_REPORT = {
  session_id: "mock-session-001",
  disposition: "PASS",
  quality_class: "Class A",
  confidence: 0.95,
  iso_5817_level: "B",
  disposition_rationale: "All checks passed.",
  root_cause: "No defects detected.",
  corrective_actions: [] as string[],
  standards_references: [] as string[],
  primary_defect_categories: [] as string[],
  threshold_violations: [] as object[],
  self_check_passed: true,
  self_check_notes: "OK",
  report_timestamp: "2026-01-01T00:00:00Z",
};

jest.mock("@/components/analysis/AnalysisTimeline", () => {
  const React = require("react") as typeof import("react");
  return {
    AnalysisTimeline: ({
      sessionId,
      streamTrigger,
      onError,
      onComplete,
      onReanalyse,
      welderDisplayName,
    }: {
      sessionId: string;
      streamTrigger: number;
      onError: (m: string) => void;
      onComplete?: (r: typeof MOCK_REPORT) => void;
      onReanalyse?: () => void;
      welderDisplayName?: string | null;
    }) => {
      const [phase, setPhase] = React.useState<"stream" | "done">("stream");
      React.useEffect(() => {
        setPhase("stream");
      }, [streamTrigger]);
      return (
        <div
          data-testid="analysis-timeline"
          data-session-id={sessionId}
          data-stream-trigger={String(streamTrigger)}
        >
          {phase === "stream" ? (
            <>
              <button
                data-testid="complete-stream-btn"
                type="button"
                onClick={() => {
                  setPhase("done");
                  onComplete?.({ ...MOCK_REPORT, session_id: sessionId });
                }}
              >
                Complete Stream
              </button>
              <button
                data-testid="error-stream-btn"
                type="button"
                onClick={() => onError("pipeline timeout")}
              >
                Error Stream
              </button>
            </>
          ) : (
            <div
              data-testid="quality-report-card"
              data-disposition={MOCK_REPORT.disposition}
            >
              <span data-testid="welder-display-name">{welderDisplayName}</span>
              {onReanalyse && (
                <button
                  data-testid="reanalyse-btn"
                  type="button"
                  onClick={onReanalyse}
                >
                  Re-analyse
                </button>
              )}
            </div>
          )}
        </div>
      );
    },
  };
});

jest.mock("@/components/analysis/StatusBadge", () => ({
  StatusBadge: ({ disposition }: { disposition: string | null }) => (
    <span data-testid="status-badge">{disposition ?? "null"}</span>
  ),
}));

import AnalysisPage from "../page";

/** Flush microtasks so mount `useEffect` health poll’s `setHealth` runs inside act(). */
async function renderAnalysisPage() {
  const utils = render(<AnalysisPage />);
  await act(async () => {
    await Promise.resolve();
  });
  return utils;
}

const MOCK_HEALTH_OK = {
  graph_initialised: true,
  classifier_initialised: true,
};
const MOCK_HEALTH_DOWN = {
  graph_initialised: false,
  classifier_initialised: false,
};

beforeEach(() => {
  mockFetchWarpHealth.mockResolvedValue(MOCK_HEALTH_OK);
  mockFetchWarpReport.mockResolvedValue(null);
  mockFetchMockSessions.mockResolvedValue([
    {
      session_id: "mock-session-001",
      welder_id: "expert_aluminium_001",
      welder_name: "Aluminium Expert 01",
      arc_type: "stitch",
      arc_on_ratio: 0.8,
      disposition: null,
      started_at: "2026-01-01T00:00:00Z",
    },
  ]);
});

afterEach(() => {
  jest.clearAllMocks();
});

describe("AnalysisPage", () => {
  it("renders without crashing and shows the empty-state prompt", async () => {
    await renderAnalysisPage();

    expect(
      screen.getByText(/select a session to begin analysis/i),
    ).toBeInTheDocument();
    expect(screen.getByTestId("session-list")).toBeInTheDocument();
    expect(screen.queryByTestId("welder-trend-chart")).not.toBeInTheDocument();
  });

  it("fires fetchWarpHealth on mount and displays system OK", async () => {
    await renderAnalysisPage();

    await waitFor(() => {
      expect(mockFetchWarpHealth).toHaveBeenCalledTimes(1);
    });

    // poll() resolves asynchronously; wait for setHealth to flush to the DOM.
    await waitFor(() => {
      expect(screen.getByText(/system: ok/i)).toBeInTheDocument();
    });
  });

  it("polls fetchWarpHealth every 30 s", async () => {
    jest.useFakeTimers();
    try {
      await renderAnalysisPage();

      await waitFor(() =>
        expect(mockFetchWarpHealth).toHaveBeenCalledTimes(1),
      );

      await act(async () => {
        jest.advanceTimersByTime(30_000);
      });

      await waitFor(() =>
        expect(mockFetchWarpHealth).toHaveBeenCalledTimes(2),
      );
    } finally {
      jest.useRealTimers();
    }
  });

  it("shows AI unavailable banner when health is down", async () => {
    mockFetchWarpHealth.mockResolvedValue(MOCK_HEALTH_DOWN);
    await renderAnalysisPage();

    await waitFor(() =>
      expect(screen.getByText(/ai pipeline unavailable/i)).toBeInTheDocument(),
    );
  });

  it("clicking a session with no existing report starts streaming", async () => {
    mockFetchWarpReport.mockResolvedValue(null);
    await renderAnalysisPage();

    fireEvent.click(screen.getByTestId("select-session-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("analysis-timeline")).toBeInTheDocument();
    });

    expect(screen.getByTestId("analysis-timeline").dataset.sessionId).toBe(
      "mock-session-001",
    );
    expect(
      screen.queryByText(/select a session to begin analysis/i),
    ).not.toBeInTheDocument();
  });

  it("report fetch failure (non-404) shows stream error and does not start analysis", async () => {
    mockFetchWarpReport.mockRejectedValue(new Error("500 Internal Server Error"));
    await renderAnalysisPage();

    fireEvent.click(screen.getByTestId("select-session-btn"));

    await waitFor(() =>
      expect(
        screen.getByText(/could not load report for mock-session-001/i),
      ).toBeInTheDocument(),
    );

    expect(screen.queryByTestId("analysis-timeline")).not.toBeInTheDocument();
  });

  it("clicking a session with an existing report shows timeline then report after stream completes", async () => {
    mockFetchWarpReport.mockResolvedValue({
      session_id: "mock-session-001",
      disposition: "CONDITIONAL",
      quality_class: "Class B",
      confidence: 0.7,
      iso_5817_level: "C",
      disposition_rationale: "Marginal",
      root_cause: "Heat input borderline",
      corrective_actions: [],
      standards_references: [],
      primary_defect_categories: [],
      threshold_violations: [],
      self_check_passed: true,
      self_check_notes: "OK",
      report_timestamp: "2026-01-01T00:00:00Z",
    });

    await renderAnalysisPage();

    fireEvent.click(screen.getByTestId("select-session-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("analysis-timeline")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("complete-stream-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("quality-report-card")).toBeInTheDocument();
    });

    expect(screen.getByTestId("quality-report-card").dataset.disposition).toBe(
      "PASS",
    );
  });

  it("SSE complete transitions from streaming to report and passes welderDisplayName", async () => {
    mockFetchWarpReport.mockResolvedValue(null);
    await renderAnalysisPage();

    fireEvent.click(screen.getByTestId("select-session-btn"));

    await waitFor(() =>
      expect(screen.getByTestId("analysis-timeline")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("complete-stream-btn"));

    await waitFor(() =>
      expect(screen.getByTestId("quality-report-card")).toBeInTheDocument(),
    );

    expect(screen.getByTestId("quality-report-card").dataset.disposition).toBe(
      "PASS",
    );
    expect(screen.getByTestId("welder-display-name").textContent).toBe(
      "Aluminium Expert 01",
    );
    expect(screen.getByTestId("analysis-timeline")).toBeInTheDocument();
  });

  it("SSE error shows error banner and returns to empty state", async () => {
    mockFetchWarpReport.mockResolvedValue(null);
    await renderAnalysisPage();

    fireEvent.click(screen.getByTestId("select-session-btn"));

    await waitFor(() =>
      expect(screen.getByTestId("analysis-timeline")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("error-stream-btn"));

    await waitFor(() => {
      expect(screen.getByText(/pipeline timeout/i)).toBeInTheDocument();
    });

    expect(
      screen.getByText(/select a session to begin analysis/i),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("analysis-timeline")).not.toBeInTheDocument();
  });

  it("Re-analyse button restarts the stream for the selected session", async () => {
    mockFetchWarpReport.mockResolvedValue(null);
    await renderAnalysisPage();

    fireEvent.click(screen.getByTestId("select-session-btn"));

    await waitFor(() =>
      expect(screen.getByTestId("analysis-timeline")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("complete-stream-btn"));

    await waitFor(() =>
      expect(screen.getByTestId("quality-report-card")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("reanalyse-btn"));

    await waitFor(() =>
      expect(screen.getByTestId("analysis-timeline")).toBeInTheDocument(),
    );

    expect(screen.queryByTestId("quality-report-card")).not.toBeInTheDocument();
  });

  it("shows WelderTrendChart with correct welderId after session select", async () => {
    mockFetchWarpReport.mockResolvedValue(null);
    await renderAnalysisPage();

    fireEvent.click(screen.getByTestId("select-session-btn"));

    await waitFor(() =>
      expect(screen.getByTestId("welder-trend-chart")).toBeInTheDocument(),
    );

    expect(screen.getByTestId("welder-trend-chart").dataset.welderId).toBe(
      "expert_aluminium_001",
    );
  });

  it("dismissing the error banner hides it", async () => {
    mockFetchWarpReport.mockResolvedValue(null);
    await renderAnalysisPage();

    fireEvent.click(screen.getByTestId("select-session-btn"));

    await waitFor(() =>
      expect(screen.getByTestId("analysis-timeline")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("error-stream-btn"));

    await waitFor(() =>
      expect(screen.getByText(/pipeline timeout/i)).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("button", { name: /dismiss error/i }));

    expect(screen.queryByText(/pipeline timeout/i)).not.toBeInTheDocument();
  });

  it("retry button on error banner restarts the stream for the selected session", async () => {
    mockFetchWarpReport.mockResolvedValue(null);
    await renderAnalysisPage();

    fireEvent.click(screen.getByTestId("select-session-btn"));
    await waitFor(() =>
      expect(screen.getByTestId("analysis-timeline")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("error-stream-btn"));
    await waitFor(() =>
      expect(screen.getByText(/analysis failed/i)).toBeInTheDocument(),
    );

    const retryBtn = screen.getByRole("button", { name: /retry analysis/i });
    expect(retryBtn).toBeInTheDocument();

    fireEvent.click(retryBtn);
    await waitFor(() =>
      expect(screen.getByTestId("analysis-timeline")).toBeInTheDocument(),
    );

    expect(screen.getByTestId("analysis-timeline").dataset.sessionId).toBe(
      "mock-session-001",
    );

    expect(screen.queryByText(/analysis failed/i)).not.toBeInTheDocument();
  });

  it("Analyse All advances queue to second session after first stream completes", async () => {
    mockFetchWarpReport.mockResolvedValue(null);
    // Mount effect and Analyse All both call fetchMockSessions — use stable mock, not Once.
    mockFetchMockSessions.mockResolvedValue([
      {
        session_id: "mock-session-001",
        welder_id: "expert_aluminium_001",
        welder_name: "Aluminium Expert 01",
        arc_type: "stitch",
        arc_on_ratio: 0.8,
        disposition: null,
        started_at: "2026-01-01T00:00:00Z",
      },
      {
        session_id: "mock-session-002",
        welder_id: "novice_aluminium_001",
        welder_name: "Aluminium Novice 01",
        arc_type: "continuous",
        arc_on_ratio: 0.6,
        disposition: null,
        started_at: "2026-01-02T00:00:00Z",
      },
    ]);

    await renderAnalysisPage();

    fireEvent.click(screen.getByTestId("analyse-all-btn"));

    await waitFor(() =>
      expect(screen.getByTestId("analysis-timeline")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("analysis-timeline").dataset.sessionId).toBe(
      "mock-session-001",
    );

    fireEvent.click(screen.getByTestId("complete-stream-btn"));

    await waitFor(() => {
      const stream = screen.getByTestId("analysis-timeline");
      expect(stream.dataset.sessionId).toBe("mock-session-002");
    });

    expect(screen.getByTestId("welder-trend-chart").dataset.welderId).toBe(
      "novice_aluminium_001",
    );
  });
});
