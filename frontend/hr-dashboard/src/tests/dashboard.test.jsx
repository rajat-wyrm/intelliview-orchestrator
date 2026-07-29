import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

import FilterBar from "../components/FilterBar";
import StatsCards from "../components/StatsCards";
import StatusBadge from "../components/StatusBadge";
import Pagination from "../components/Pagination";

const baseFilters = {
  search: "",
  domain: "",
  type: "",
  status: "",
  dateFrom: "",
  dateTo: "",
};

describe("Dashboard Components Unit Tests (HR-12)", () => {
  describe("FilterBar Component", () => {
    it("renders search input and dropdown controls", () => {
      render(<FilterBar filters={baseFilters} onFilterChange={() => {}} />);
      expect(screen.getByPlaceholderText("Search candidates...")).toBeInTheDocument();
      expect(screen.getByText("All Domains")).toBeInTheDocument();
      expect(screen.getByText("All Types")).toBeInTheDocument();
      expect(screen.getByText("All Status")).toBeInTheDocument();
    });

    it("triggers onFilterChange on search input change", () => {
      const handleFilterChange = vi.fn();
      render(<FilterBar filters={baseFilters} onFilterChange={handleFilterChange} />);
      const searchInput = screen.getByPlaceholderText("Search candidates...");
      fireEvent.change(searchInput, { target: { value: "John" } });
      expect(handleFilterChange).toHaveBeenCalledWith({ ...baseFilters, search: "John" });
    });

    it("triggers onFilterChange on domain selection change", () => {
      const handleFilterChange = vi.fn();
      render(<FilterBar filters={baseFilters} onFilterChange={handleFilterChange} />);
      const domainSelect = screen.getByDisplayValue("All Domains");
      fireEvent.change(domainSelect, { target: { value: "engineering" } });
      expect(handleFilterChange).toHaveBeenCalledWith({ ...baseFilters, domain: "engineering" });
    });

    it("triggers onFilterChange on status selection change", () => {
      const handleFilterChange = vi.fn();
      render(<FilterBar filters={baseFilters} onFilterChange={handleFilterChange} />);
      const statusSelect = screen.getByDisplayValue("All Status");
      fireEvent.change(statusSelect, { target: { value: "selected" } });
      expect(handleFilterChange).toHaveBeenCalledWith({ ...baseFilters, status: "selected" });
    });
  });

  describe("StatsCards Component", () => {
    it("renders all candidate metric card labels", () => {
      render(<StatsCards stats={{ total: 10, pending: 3, selected: 4, rejected: 3 }} />);
      expect(screen.getByText("Total Candidates")).toBeInTheDocument();
      expect(screen.getByText("Pending")).toBeInTheDocument();
      expect(screen.getByText("Selected")).toBeInTheDocument();
      expect(screen.getByText("Rejected")).toBeInTheDocument();
    });

    it("displays correct numerical stat values", () => {
      render(<StatsCards stats={{ total: 15, pending: 5, selected: 8, rejected: 2 }} />);
      expect(screen.getByText("15")).toBeInTheDocument();
      expect(screen.getByText("5")).toBeInTheDocument();
      expect(screen.getByText("8")).toBeInTheDocument();
      expect(screen.getByText("2")).toBeInTheDocument();
    });

    it("falls back to 0 when stats prop is undefined or null", () => {
      render(<StatsCards stats={undefined} />);
      const zeroLabels = screen.getAllByText("0");
      expect(zeroLabels.length).toBe(4);
    });

    it("handles partial stats objects with fallback values", () => {
      render(<StatsCards stats={{ total: 7 }} />);
      expect(screen.getByText("7")).toBeInTheDocument();
      const zeroLabels = screen.getAllByText("0");
      expect(zeroLabels.length).toBe(3);
    });
  });

  describe("StatusBadge Component", () => {
    it("renders fallback dash when status is missing or null", () => {
      render(<StatusBadge status={undefined} />);
      expect(screen.getByText("—")).toBeInTheDocument();
    });

    it("replaces underscores with spaces in status string", () => {
      render(<StatusBadge status="under_review" />);
      expect(screen.getByText("under review")).toBeInTheDocument();
    });

    it("applies success variant for completed status", () => {
      const { container } = render(<StatusBadge status="COMPLETED" />);
      expect(screen.getByText("COMPLETED")).toBeInTheDocument();
      expect(container.firstChild.className).toContain("emerald");
    });

    it("applies warn variant for pending status", () => {
      const { container } = render(<StatusBadge status="pending" />);
      expect(screen.getByText("pending")).toBeInTheDocument();
      expect(container.firstChild.className).toContain("amber");
    });

    it("applies danger variant for failed status", () => {
      const { container } = render(<StatusBadge status="FAILED" />);
      expect(screen.getByText("FAILED")).toBeInTheDocument();
      expect(container.firstChild.className).toContain("rose");
    });

    it("applies muted variant for unrecognized status", () => {
      const { container } = render(<StatusBadge status="unknown_state" />);
      expect(screen.getByText("unknown state")).toBeInTheDocument();
      expect(container.firstChild.className).toContain("zinc");
    });
  });

  describe("Pagination Component", () => {
    it("displays current page and total pages count", () => {
      render(<Pagination currentPage={3} totalPages={10} onPageChange={() => {}} />);
      expect(screen.getByText("Page 3 of 10")).toBeInTheDocument();
    });

    it("disables Previous button on the first page", () => {
      render(<Pagination currentPage={1} totalPages={5} onPageChange={() => {}} />);
      expect(screen.getByText("Previous")).toBeDisabled();
    });

    it("disables Next button on the last page", () => {
      render(<Pagination currentPage={5} totalPages={5} onPageChange={() => {}} />);
      expect(screen.getByText("Next")).toBeDisabled();
    });

    it("invokes onPageChange with incremented page on Next button click", () => {
      const handlePageChange = vi.fn();
      render(<Pagination currentPage={2} totalPages={5} onPageChange={handlePageChange} />);
      fireEvent.click(screen.getByText("Next"));
      expect(handlePageChange).toHaveBeenCalledWith(3);
    });

    it("invokes onPageChange with decremented page on Previous button click", () => {
      const handlePageChange = vi.fn();
      render(<Pagination currentPage={4} totalPages={5} onPageChange={handlePageChange} />);
      fireEvent.click(screen.getByText("Previous"));
      expect(handlePageChange).toHaveBeenCalledWith(3);
    });
  });
});
