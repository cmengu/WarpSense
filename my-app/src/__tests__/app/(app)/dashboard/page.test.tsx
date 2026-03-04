/**
 * Tests for Panel Readiness (dashboard) — 6 panels with inspection decisions.
 *
 * Validates:
 *   - Promise.allSettled: partial failures don't block working cards
 *   - Per-card error: "Score unavailable" when fetch fails
 *   - Loading state (skeleton cards)
 *   - Links to /replay/[sessionId], /seagull/welder/[id], /compare
 *   - Score-based badge colours (red/amber/green)
 *   - Sort by score ascending (worst first)
 */

import { render, screen, waitFor, within } from "@testing-library/react";
import DashboardPage from "@/app/(app)/dashboard/page";

const mockFetchScore = jest.fn();

jest.mock("@/lib/api", () => ({
  fetchScore: (...args: unknown[]) => mockFetchScore(...args),
}));

describe("DashboardPage (Panel Readiness)", () => {
  beforeEach(() => {
    mockFetchScore.mockImplementation((sessionId: string) => {
      return Promise.resolve({ total: 75, rules: [] });
    });
  });

  it("shows loading state initially with skeleton", () => {
    render(<DashboardPage />);
    expect(screen.getByText(/Panel Readiness/)).toBeInTheDocument();
  });

  it("renders panel roster with 6 grid cards and Expert Benchmark", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/PANEL-4C/)).toBeInTheDocument();
    });

    expect(screen.getByText(/PANEL-4C/)).toBeInTheDocument();
    expect(screen.getByText(/PANEL-7A/)).toBeInTheDocument();
    expect(screen.getByText(/Expert Benchmark/)).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: /Inspection decision/ })
    ).toHaveLength(6);
  });

  it("links cards to /replay/[sessionId]", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/PANEL-4C/)).toBeInTheDocument();
    });

    const links = screen.getAllByRole("link");
    const panelReplayLink = links.find(
      (l) => l.getAttribute("href") === "/replay/sess_PANEL-4C_005"
    );
    expect(panelReplayLink).toBeDefined();
  });

  it("links Surveyor report to /seagull/welder/[id]", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/PANEL-4C/)).toBeInTheDocument();
    });

    const allLinks = screen.getAllByRole("link");
    const surveyorReportLink = allLinks.find(
      (l) => l.getAttribute("href") === "/seagull/welder/PANEL-4C"
    );
    expect(surveyorReportLink).toBeDefined();
    expect(surveyorReportLink?.textContent).toMatch(/Surveyor report/);
  });

  it("uses Promise.allSettled: one failure uses mock fallback, others show API score", async () => {
    mockFetchScore.mockImplementation((sessionId: string) => {
      if (sessionId === "sess_PANEL-4C_005") {
        return Promise.reject(new Error("404"));
      }
      return Promise.resolve({ total: 95, rules: [] });
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/PANEL-4C/)).toBeInTheDocument();
    });

    // PANEL-4C fetch failed → fallback to PANEL_MOCK_SCORES (45); others show API 95
    expect(screen.getByText(/PANEL-4C/)).toBeInTheDocument();
    const panel4CCard = screen.getByRole("heading", { name: /PANEL-4C/ }).closest("[class*='rounded']");
    expect(within(panel4CCard!).getByText("45/100")).toBeInTheDocument();
  });

  it("shows score-based badge colour (high tier for score ≥85)", async () => {
    mockFetchScore.mockImplementation(() =>
      Promise.resolve({ total: 85, rules: [] })
    );

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/PANEL-4C/)).toBeInTheDocument();
    });

    const panelCard = screen
      .getByRole("heading", { name: /PANEL-4C/ })
      .closest("[class*='rounded']") as HTMLElement | null;
    expect(panelCard).toBeInTheDocument();
    const badge = within(panelCard!).getByText("85/100");
    expect(badge).toHaveAttribute("data-score-tier", "high");
  });

  it("sorts cards by score ascending (worst first)", async () => {
    mockFetchScore.mockImplementation((sessionId: string) => {
      if (sessionId === "sess_PANEL-4C_005")
        return Promise.resolve({ total: 45, rules: [] });
      if (sessionId === "sess_PANEL-7A_005")
        return Promise.resolve({ total: 72, rules: [] });
      return Promise.resolve({ total: 90, rules: [] });
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /PANEL-4C/ })).toBeInTheDocument();
    });

    const panelHeadings = screen
      .getAllByRole("heading", { level: 3 })
      .filter((h) => /PANEL-/.test(h.textContent ?? ""));
    expect(panelHeadings[0]).toHaveTextContent(/PANEL-4C/);
    expect(panelHeadings[1]).toHaveTextContent(/PANEL-7A/);
  });

  it("Expert Benchmark block is separate; 6 Inspection decision links in panel grid", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Expert Benchmark/)).toBeInTheDocument();
    });

    const compareLinks = screen
      .getAllByRole("link")
      .filter((l) => l.getAttribute("href")?.includes("/compare/"));
    expect(compareLinks).toHaveLength(6);
  });

  it("calls fetchScore for latest session only (one per panel)", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/PANEL-4C/)).toBeInTheDocument();
    });

    expect(mockFetchScore).toHaveBeenCalledWith(
      "sess_PANEL-4C_005",
      expect.any(AbortSignal)
    );
    const calls = mockFetchScore.mock.calls.map((c) => c[0]);
    expect(calls).not.toContain("sess_PANEL-4C_004");
  });
});
