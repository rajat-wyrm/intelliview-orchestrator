"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { ChevronLeft, ChevronRight } from "lucide-react";

function Pagination(){
    const[currentPage, setCurrentPage] = useState(1);
    const[limit,setLimit] = useState(10);

    const totalCount =45;
    const totalPages = Math.ceil(totalCount / limit);

    const startItem =(currentPage -1) * limit +1;
    const endItem = Math.min(currentPage * limit, totalCount);

    const pageNumbers =[];

    for(
        let i = Math.max(1,currentPage -2);
        i <= Math.min(totalPages,currentPage +2);
        i++
    ){
        pageNumbers.push(i);
    }

    return(
        
  <div className="flex items-center justify-between border-t border-border p-4">

    <div className="text-sm text-muted">
      Showing {startItem}-{endItem} of {totalCount} results
    </div>

    <div className="flex items-center gap-2">

      <button
        onClick={() => setCurrentPage(currentPage - 1)}
        disabled={currentPage === 1}
        className="rounded border px-3 py-1 disabled:opacity-50"
      >
        <ChevronLeft size={16} />
      </button>

      {pageNumbers.map((page) => (
  <button
    key={page}
    onClick={() => setCurrentPage(page)}
    className={cn(
      "rounded border px-3 py-1",
      currentPage === page
        ? "bg-accent text-white"
        : "bg-white"
    )}
  >
    {page}
  </button>
))}

      <button
        onClick={() => setCurrentPage(currentPage + 1)}
        disabled={currentPage === totalPages}
        className="rounded border px-3 py-1 disabled:opacity-50"
      >
        <ChevronRight size={16} />
      </button>

      <select
        value={limit}
        onChange={(e) => {
          setLimit(Number(e.target.value));
          setCurrentPage(1);
        }}
        className="rounded border px-2 py-1"
      >
        <option value={10}>10</option>
        <option value={25}>25</option>
        <option value={50}>50</option>
      </select>

    </div>
  </div>
);
}

export { Pagination };