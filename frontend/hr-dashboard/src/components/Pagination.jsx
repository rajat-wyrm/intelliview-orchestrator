"use client";

function Pagination({ currentPage, totalPages, onPageChange }) {
  const handlePrev = () => {
    if (currentPage > 1) onPageChange(currentPage - 1);
  };

  const handleNext = () => {
    if (currentPage < totalPages) onPageChange(currentPage + 1);
  };

  return (
    <div className="flex items-center justify-between gap-3">
      <button
        onClick={handlePrev}
        disabled={currentPage === 1}
        className="rounded-md border border-border bg-bg-card px-3 py-1.5 text-sm text-zinc-100 hover:bg-bg-panel disabled:cursor-not-allowed disabled:opacity-40"
      >
        Previous
      </button>

      <span className="text-sm text-muted">
        Page {currentPage} of {totalPages || 1}
      </span>

      <button
        onClick={handleNext}
        disabled={currentPage === totalPages || totalPages === 0}
        className="rounded-md border border-border bg-bg-card px-3 py-1.5 text-sm text-zinc-100 hover:bg-bg-panel disabled:cursor-not-allowed disabled:opacity-40"
      >
        Next
      </button>
    </div>
  );
}

export default Pagination;