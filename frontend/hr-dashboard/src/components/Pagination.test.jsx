import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import Pagination from "./Pagination";

describe("Pagination", () => {
  it("displays the current page and total pages", () => {
    render(<Pagination currentPage={2} totalPages={5} onPageChange={() => {}} />);
    expect(screen.getByText("Page 2 of 5")).toBeInTheDocument();
  });

  it("disables Previous button on the first page", () => {
    render(<Pagination currentPage={1} totalPages={5} onPageChange={() => {}} />);
    expect(screen.getByText("Previous")).toBeDisabled();
  });

  it("disables Next button on the last page", () => {
    render(<Pagination currentPage={5} totalPages={5} onPageChange={() => {}} />);
    expect(screen.getByText("Next")).toBeDisabled();
  });

  it("calls onPageChange with the next page number when Next is clicked", () => {
    const handlePageChange = vi.fn();
    render(<Pagination currentPage={2} totalPages={5} onPageChange={handlePageChange} />);
    fireEvent.click(screen.getByText("Next"));
    expect(handlePageChange).toHaveBeenCalledWith(3);
  });

  it("calls onPageChange with the previous page number when Previous is clicked", () => {
    const handlePageChange = vi.fn();
    render(<Pagination currentPage={2} totalPages={5} onPageChange={handlePageChange} />);
    fireEvent.click(screen.getByText("Previous"));
    expect(handlePageChange).toHaveBeenCalledWith(1);
  });
});