import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import StatusBadge from "./StatusBadge";

describe("StatusBadge", () => {
  it("renders fallback dash when status is missing or empty", () => {
    render(<StatusBadge status={undefined} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("replaces underscores with spaces in status label", () => {
    render(<StatusBadge status="in_progress" />);
    expect(screen.getByText("in progress")).toBeInTheDocument();
  });

  it("applies success styling for completed status", () => {
    const { container } = render(<StatusBadge status="COMPLETED" />);
    expect(screen.getByText("COMPLETED")).toBeInTheDocument();
    expect(container.firstChild.className).toContain("emerald");
  });

  it("applies warning styling for pending status", () => {
    const { container } = render(<StatusBadge status="pending" />);
    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(container.firstChild.className).toContain("amber");
  });

  it("applies danger styling for failed status", () => {
    const { container } = render(<StatusBadge status="FAILED" />);
    expect(screen.getByText("FAILED")).toBeInTheDocument();
    expect(container.firstChild.className).toContain("rose");
  });

  it("applies muted styling for unknown status", () => {
    const { container } = render(<StatusBadge status="custom_status" />);
    expect(screen.getByText("custom status")).toBeInTheDocument();
    expect(container.firstChild.className).toContain("zinc");
  });
});
