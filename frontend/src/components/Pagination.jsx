"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { ChevronLeft, ChevronRight } from "lucide-react";

function Pagination() {
  const [currentPage, setCurrentPage] = useState(1);
  const [limit, setLimit] = useState(10);

  const totalCount = 45;
  const totalPages = Math.ceil(totalCount / limit);

  const startItem = (currentPage - 1) * limit + 1;
  const endItem = Math.min(currentPage * limit, totalCount);

  const pageNumbers = [];

  for (
    let i = Math.max(1, currentPage - 2);
    i <= Math.min(totalPages, currentPage + 2);
    i++
  ) {
    pageNumbers.push(i);
  }

  return (
    <nav
      className="flex flex-col gap-3 border-t border-border p-4 md:flex-row md:items-center md:justify-between"
      aria-label="Pagination Navigation"
    >
      <div
        className="text-sm text-zinc-400"
        aria-live="polite"
      >
        Showing <strong>{startItem}</strong>–<strong>{endItem}</strong> of{" "}
        <strong>{totalCount}</strong> results
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          aria-label="Previous Page"
          title="Previous Page"
          onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
          disabled={currentPage === 1}
          className="rounded-md border border-border bg-bg-card p-2 text-zinc-300 transition-colors hover:bg-bg-panel hover:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-bg-panel disabled:cursor-not-allowed disabled:opacity-50"
        >
          <ChevronLeft size={16} aria-hidden="true" />
        </button>

        {pageNumbers.map((page) => (
          <button
            key={page}
            type="button"
            aria-label={`Go to page ${page}`}
            aria-current={currentPage === page ? "page" : undefined}
            onClick={() => setCurrentPage(page)}
            className={cn(
              "min-w-[38px] rounded-md border px-3 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-bg-panel",
              currentPage === page
                ? "border-accent bg-accent text-white"
                : "border-border bg-bg-card text-zinc-300 hover:bg-bg-panel hover:text-white"
            )}
          >
            {page}
          </button>
        ))}

        <button
          type="button"
          aria-label="Next Page"
          title="Next Page"
          onClick={() =>
            setCurrentPage((p) => Math.min(totalPages, p + 1))
          }
          disabled={currentPage === totalPages}
          className="rounded-md border border-border bg-bg-card p-2 text-zinc-300 transition-colors hover:bg-bg-panel hover:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-bg-panel disabled:cursor-not-allowed disabled:opacity-50"
        >
          <ChevronRight size={16} aria-hidden="true" />
        </button>

        <label htmlFor="rows-per-page" className="sr-only">
          Rows per page
        </label>

        <select
          id="rows-per-page"
          aria-label="Rows per page"
          value={limit}
          onChange={(e) => {
            setLimit(Number(e.target.value));
            setCurrentPage(1);
          }}
          className="rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-300 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-bg-panel"
        >
          <option value={10}>10 / page</option>
          <option value={25}>25 / page</option>
          <option value={50}>50 / page</option>
        </select>
      </div>
    </nav>
  );
}

export { Pagination };