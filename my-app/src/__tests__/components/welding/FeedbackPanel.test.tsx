/**
 * Tests for FeedbackPanel (Seagull pilot Step 4 + WarpSense Micro-Feedback).
 *
 * Validates:
 *   - Renders items with severity styling (info → blue, warning → violet, critical → amber)
 *   - Layout: space-y-3, rounded card, border-l-4
 *   - Icons: ℹ️ (info), ⚠️ (warning), ⛔ (critical)
 *   - Suggestion appears when present
 *   - Session-level items (no frameIndex/type) render non-interactive
 *   - Micro items with frameIndex+type+frames+onFrameSelect are clickable
 */

import { render, screen, fireEvent } from "@testing-library/react";
import FeedbackPanel from "@/components/welding/FeedbackPanel";
import type { FeedbackItem } from "@/types/ai-feedback";
import type { Frame } from "@/types/frame";

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

const mockCriticalItem: FeedbackItem = {
  severity: "critical",
  message: "Torch angle drifted 15° at frame 100 — keep within ±5°",
  timestamp_ms: null,
  suggestion: "Maintain consistent work angle.",
};

const mockMicroItem: FeedbackItem = {
  severity: "warning",
  message: "Torch angle drifted 12° at frame 5",
  timestamp_ms: null,
  suggestion: "Maintain work angle.",
  frameIndex: 5,
  type: "angle",
};

/** Minimal frames for jump-to-frame tests; FeedbackPanel only needs timestamp_ms. */
const mockFrames: Frame[] = [
  { timestamp_ms: 0, volts: 0, amps: 0, angle_degrees: 0, thermal_snapshots: [], has_thermal_data: false, optional_sensors: null, heat_dissipation_rate_celsius_per_sec: null },
  { timestamp_ms: 10, volts: 0, amps: 0, angle_degrees: 0, thermal_snapshots: [], has_thermal_data: false, optional_sensors: null, heat_dissipation_rate_celsius_per_sec: null },
  { timestamp_ms: 20, volts: 0, amps: 0, angle_degrees: 0, thermal_snapshots: [], has_thermal_data: false, optional_sensors: null, heat_dissipation_rate_celsius_per_sec: null },
  { timestamp_ms: 30, volts: 0, amps: 0, angle_degrees: 0, thermal_snapshots: [], has_thermal_data: false, optional_sensors: null, heat_dissipation_rate_celsius_per_sec: null },
  { timestamp_ms: 40, volts: 0, amps: 0, angle_degrees: 0, thermal_snapshots: [], has_thermal_data: false, optional_sensors: null, heat_dissipation_rate_celsius_per_sec: null },
  { timestamp_ms: 50, volts: 0, amps: 0, angle_degrees: 0, thermal_snapshots: [], has_thermal_data: false, optional_sensors: null, heat_dissipation_rate_celsius_per_sec: null },
  { timestamp_ms: 60, volts: 0, amps: 0, angle_degrees: 0, thermal_snapshots: [], has_thermal_data: false, optional_sensors: null, heat_dissipation_rate_celsius_per_sec: null },
];

describe("FeedbackPanel", () => {
  it("renders info item with blue styling", () => {
    render(<FeedbackPanel items={[mockInfoItem]} />);
    expect(screen.getByText(/Angle within target/)).toBeInTheDocument();
    const card = screen.getByText(/Angle within target/).closest(".border-blue-500");
    expect(card).toHaveClass("bg-blue-50");
  });

  it("renders warning item with violet styling", () => {
    render(<FeedbackPanel items={[mockWarningItem]} />);
    expect(screen.getByText(/Current fluctuated/)).toBeInTheDocument();
    const card = screen.getByText(/Current fluctuated/).closest(".border-violet-500");
    expect(card).toHaveClass("bg-violet-50");
  });

  it("renders critical item with amber styling", () => {
    render(<FeedbackPanel items={[mockCriticalItem]} />);
    expect(screen.getByText(/Torch angle drifted 15°/)).toBeInTheDocument();
    const card = screen.getByText(/Torch angle drifted 15°/).closest(".border-amber-500");
    expect(card).toHaveClass("bg-amber-50");
  });

  it("shows info icon for info items", () => {
    render(<FeedbackPanel items={[mockInfoItem]} />);
    const card = screen.getByText(/Angle within target/).closest(".border-blue-500");
    expect(card?.textContent).toContain("ℹ️");
  });

  it("shows warning icon for warning items", () => {
    render(<FeedbackPanel items={[mockWarningItem]} />);
    const card = screen.getByText(/Current fluctuated/).closest(".border-violet-500");
    expect(card?.textContent).toContain("⚠️");
  });

  it("shows critical icon for critical items", () => {
    render(<FeedbackPanel items={[mockCriticalItem]} />);
    const card = screen.getByText(/Torch angle drifted 15°/).closest(".border-amber-500");
    expect(card?.textContent).toContain("⛔");
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

  it("session-level items without frameIndex are not clickable", () => {
    const onFrameSelect = jest.fn();
    render(
      <FeedbackPanel items={[mockWarningItem]} frames={mockFrames} onFrameSelect={onFrameSelect} />
    );
    const el = screen.getByText(/Current fluctuated/).closest("div");
    expect(el?.tagName).not.toBe("BUTTON");
    expect(onFrameSelect).not.toHaveBeenCalled();
  });

  it("items with frameIndex but no type are not clickable", () => {
    const itemNoType: FeedbackItem = {
      ...mockMicroItem,
      type: undefined,
    };
    const onFrameSelect = jest.fn();
    render(
      <FeedbackPanel items={[itemNoType]} frames={mockFrames} onFrameSelect={onFrameSelect} />
    );
    const el = screen.getByText(/Torch angle drifted 12°/).closest("div");
    expect(el?.tagName).not.toBe("BUTTON");
  });

  it("micro item with frames and onFrameSelect is clickable and triggers callback", () => {
    const onFrameSelect = jest.fn();
    render(
      <FeedbackPanel
        items={[mockMicroItem]}
        frames={mockFrames}
        onFrameSelect={onFrameSelect}
      />
    );
    const button = screen.getByRole("button", { name: /Jump to frame 5/ });
    expect(button).toHaveAttribute("data-testid", "micro-feedback-item");
    fireEvent.click(button);
    expect(onFrameSelect).toHaveBeenCalledWith(50); // frame 5 has timestamp_ms 50
  });
});
