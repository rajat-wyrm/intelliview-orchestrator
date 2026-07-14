import React from "react";

function Pagination({ currentPage, totalPages, onPageChange }) {
  const handlePrev = () => {
    if (currentPage > 1) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNext = () => {
    if (currentPage < totalPages) {
      onPageChange(currentPage + 1);
    }
  };

  return (
    <div className="pagination">
      <button onClick={handlePrev} disabled={currentPage === 1}>
        Previous
      </button>

      <span>
        Page {currentPage} of {totalPages || 1}
      </span>

      <button onClick={handleNext} disabled={currentPage === totalPages || totalPages === 0}>
        Next
      </button>
    </div>
  );
}

export default Pagination;