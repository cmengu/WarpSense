/**
 * Tests for FeedbackPanel (Seagull pilot Step 4).
 *
 * Validates:
 *   - Renders items with severity styling (info → blue, warning → amber)
 *   - Layout: space-y-3, rounded card, border-l-4
 *   - Icons: ℹ️ (info), ⚠️ (warning)
 *   - Suggestion appears when present
 */

import { render, screen } from "@testing-library/react";
import FeedbackPanel from "@/components/welding/FeedbackPanel";
import type { FeedbackItem } from "@/types/ai-feedback";

const mockInfoItem: FeedbackItem = {
  severity: "info",
  message: "Angle within target.",
  timestamp_ms: null,
  suggestion: null,
};

const mockWarningItem: FeedbackItem = {
  severity: "warning",
  message: "Current fluctuated by 5.2A — aim for stability under 3A",
  timestamp_ms: null,
  suggestion: "Improve amps stability.",
};

describe("FeedbackPanel", () => {
  it("renders info item with blue styling", () => {
    render(<FeedbackPanel items={[mockInfoItem]} />);
    expect(screen.getByText(/Angle within target/)).toBeInTheDocument();
    const card = screen.getByText(/Angle within target/).closest(".border-blue-500");
    expect(card).toHaveClass("bg-blue-50");
  });

  it("renders warning item with amber styling", () => {
    render(<FeedbackPanel items={[mockWarningItem]} />);
    expect(screen.getByText(/Current fluctuated/)).toBeInTheDocument();
    const card = screen.getByText(/Current fluctuated/).closest(".border-amber-500");
    expect(card).toHaveClass("bg-amber-50");
  });

  it("shows info icon for info items", () => {
    render(<FeedbackPanel items={[mockInfoItem]} />);
    const card = screen.getByText(/Angle within target/).closest(".border-blue-500");
    expect(card?.textContent).toContain("ℹ️");
  });

  it("shows warning icon for warning items", () => {
    render(<FeedbackPanel items={[mockWarningItem]} />);
    const card = screen.getByText(/Current fluctuated/).closest(".border-amber-500");
    expect(card?.textContent).toContain("⚠️");
  });

  it("shows suggestion when present", () => {
    render(<FeedbackPanel items={[mockWarningItem]} />);
    expect(screen.getByText(/💡 Improve amps stability/)).toBeInTheDocument();
  });

  it("does not show suggestion for info items without suggestion", () => {
    render(<FeedbackPanel items={[mockInfoItem]} />);
    expect(screen.queryByText(/💡/)).not.toBeInTheDocument();
  });

  it("renders multiple items with space-y-3 layout", () => {
    const { container } = render(
      <FeedbackPanel items={[mockInfoItem, mockWarningItem]} />
    );
    const list = container.firstChild;
    expect(list).toHaveClass("space-y-3");
    expect(screen.getByText(/Angle within target/)).toBeInTheDocument();
    expect(screen.getByText(/Current fluctuated/)).toBeInTheDocument();
  });

  it("renders empty list without error", () => {
    const { container } = render(<FeedbackPanel items={[]} />);
    expect(container.firstChild).toBeInTheDocument();
  });
});
