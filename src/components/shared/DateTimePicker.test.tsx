import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DateTimePicker } from "./DateTimePicker";

const ISO_DATE = "2026-03-14T09:00";

function renderPicker(props: Partial<React.ComponentProps<typeof DateTimePicker>> = {}) {
  const onChange = vi.fn();
  render(<DateTimePicker value="" onChange={onChange} {...props} />);
  return { onChange };
}

async function openPopover() {
  await userEvent.click(screen.getByRole("button", { name: /select date|mar|jan|feb|apr|may|jun|jul|aug|sep|oct|nov|dec/i }));
}

describe("DateTimePicker", () => {
  // ── Trigger display ──────────────────────────────────────────────────────

  it("shows the placeholder when value is empty", () => {
    renderPicker({ placeholder: "Pick a date" });
    expect(screen.getByText("Pick a date")).toBeInTheDocument();
  });

  it("shows formatted date when a value is provided", () => {
    renderPicker({ value: ISO_DATE });
    expect(screen.getByText(/Mar 14, 2026/)).toBeInTheDocument();
  });

  it("includes the time in the label when includeTime=true", () => {
    renderPicker({ value: ISO_DATE, includeTime: true });
    expect(screen.getByText(/09:00/)).toBeInTheDocument();
  });

  it("omits the time in the label when includeTime=false", () => {
    renderPicker({ value: "2026-03-14", includeTime: false });
    expect(screen.queryByText(/09:00/)).not.toBeInTheDocument();
  });

  // ── Open / close ─────────────────────────────────────────────────────────

  it("popover is not shown initially", () => {
    renderPicker();
    expect(screen.queryByText("January")).not.toBeInTheDocument();
    expect(screen.queryByText("March")).not.toBeInTheDocument();
  });

  it("opens the popover when the trigger is clicked", async () => {
    renderPicker({ value: ISO_DATE });
    await userEvent.click(screen.getByRole("button", { name: /Mar 14/ }));
    expect(screen.getByText("March 2026")).toBeInTheDocument();
  });

  it("closes the popover when Escape is pressed", async () => {
    renderPicker({ value: ISO_DATE });
    await userEvent.click(screen.getByRole("button", { name: /Mar 14/ }));
    expect(screen.getByText("March 2026")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByText("March 2026")).not.toBeInTheDocument();
  });

  it("does not open when disabled", async () => {
    renderPicker({ value: ISO_DATE, disabled: true });
    const trigger = screen.getByRole("button", { name: /Mar 14/ });
    expect(trigger).toBeDisabled();
    await userEvent.click(trigger);
    expect(screen.queryByText("March 2026")).not.toBeInTheDocument();
  });

  // ── Day selection ─────────────────────────────────────────────────────────

  it("calls onChange when a day is clicked", async () => {
    const { onChange } = renderPicker({ value: ISO_DATE, includeTime: false });
    await userEvent.click(screen.getByRole("button", { name: /Mar 14/ }));
    // Click day 20
    const day20 = screen.getAllByRole("button").find((b) => b.textContent === "20");
    await userEvent.click(day20!);
    expect(onChange).toHaveBeenCalledWith("2026-03-20");
  });

  it("calls onChange with the time preserved when a day is clicked with includeTime=true", async () => {
    const { onChange } = renderPicker({ value: ISO_DATE, includeTime: true });
    await userEvent.click(screen.getByRole("button", { name: /Mar 14/ }));
    const day20 = screen.getAllByRole("button").find((b) => b.textContent === "20");
    await userEvent.click(day20!);
    expect(onChange).toHaveBeenCalledWith("2026-03-20T09:00");
  });

  // ── Month navigation ──────────────────────────────────────────────────────

  it("navigates to the previous month", async () => {
    renderPicker({ value: ISO_DATE });
    await userEvent.click(screen.getByRole("button", { name: /Mar 14/ }));
    expect(screen.getByText("March 2026")).toBeInTheDocument();
    await userEvent.click(screen.getByText("‹"));
    expect(screen.getByText("February 2026")).toBeInTheDocument();
  });

  it("navigates to the next month", async () => {
    renderPicker({ value: ISO_DATE });
    await userEvent.click(screen.getByRole("button", { name: /Mar 14/ }));
    await userEvent.click(screen.getByText("›"));
    expect(screen.getByText("April 2026")).toBeInTheDocument();
  });

  it("wraps from January to December when going to previous month", async () => {
    renderPicker({ value: "2026-01-15T09:00" });
    await userEvent.click(screen.getByRole("button", { name: /Jan 15/ }));
    await userEvent.click(screen.getByText("‹"));
    expect(screen.getByText("December 2025")).toBeInTheDocument();
  });

  // ── Clear button ──────────────────────────────────────────────────────────

  it("shows a clear button when clearable=true and a value is set", () => {
    renderPicker({ value: ISO_DATE, clearable: true });
    expect(screen.getByRole("button", { name: "Clear date" })).toBeInTheDocument();
  });

  it("calls onChange with empty string when the clear button is clicked", async () => {
    const { onChange } = renderPicker({ value: ISO_DATE, clearable: true });
    await userEvent.click(screen.getByRole("button", { name: "Clear date" }));
    expect(onChange).toHaveBeenCalledWith("");
  });

  it("does not show a clear button when clearable=false", () => {
    renderPicker({ value: ISO_DATE, clearable: false });
    expect(screen.queryByRole("button", { name: "Clear date" })).not.toBeInTheDocument();
  });

  it("does not show a clear button when value is empty even if clearable=true", () => {
    renderPicker({ value: "", clearable: true });
    expect(screen.queryByRole("button", { name: "Clear date" })).not.toBeInTheDocument();
  });

  // ── Time spinners ─────────────────────────────────────────────────────────

  it("increments the hour when the up arrow button is clicked", async () => {
    const { onChange } = renderPicker({ value: ISO_DATE, includeTime: true });
    await userEvent.click(screen.getByRole("button", { name: /Mar 14/ }));
    // The first ▲ button is the hour up spinner
    const upBtns = screen.getAllByText("▲");
    await userEvent.click(upBtns[0]);
    expect(onChange).toHaveBeenCalledWith("2026-03-14T10:00");
  });

  it("decrements the hour when the down arrow button is clicked", async () => {
    const { onChange } = renderPicker({ value: ISO_DATE, includeTime: true });
    await userEvent.click(screen.getByRole("button", { name: /Mar 14/ }));
    const downBtns = screen.getAllByText("▼");
    await userEvent.click(downBtns[0]);
    expect(onChange).toHaveBeenCalledWith("2026-03-14T08:00");
  });

  it("increments the minute by 5 when the minute up button is clicked", async () => {
    const { onChange } = renderPicker({ value: ISO_DATE, includeTime: true });
    await userEvent.click(screen.getByRole("button", { name: /Mar 14/ }));
    const upBtns = screen.getAllByText("▲");
    await userEvent.click(upBtns[1]); // second ▲ is minute
    expect(onChange).toHaveBeenCalledWith("2026-03-14T09:05");
  });

  it("wraps hour from 23 to 0 when incremented", async () => {
    const { onChange } = renderPicker({ value: "2026-03-14T23:00", includeTime: true });
    await userEvent.click(screen.getByRole("button", { name: /Mar 14/ }));
    const upBtns = screen.getAllByText("▲");
    await userEvent.click(upBtns[0]);
    expect(onChange).toHaveBeenCalledWith("2026-03-14T00:00");
  });

  // ── Done button ───────────────────────────────────────────────────────────

  it("closes the popover when Done is clicked", async () => {
    renderPicker({ value: ISO_DATE, includeTime: true });
    await userEvent.click(screen.getByRole("button", { name: /Mar 14/ }));
    expect(screen.getByText("Done")).toBeInTheDocument();
    await userEvent.click(screen.getByText("Done"));
    expect(screen.queryByText("Done")).not.toBeInTheDocument();
  });
});
