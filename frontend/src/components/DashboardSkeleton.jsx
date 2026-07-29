import React from "react";

/**
 * DashboardSkeleton.jsx
 *
 * Loading placeholder displayed while dashboard data is loading.
 * Mirrors:
 *  - StatsCards.jsx (4 cards)
 *  - CandidateTable.jsx (6 columns, 5 rows)
 *
 * Usage:
 * {isInitialLoading ? <DashboardSkeleton /> : <Dashboard />}
 */

const STAT_CARD_COUNT = 4;
const TABLE_COLUMN_COUNT = 6;
const TABLE_ROW_COUNT = 5;

const TABLE_COLUMN_WIDTHS = [
  "w-32",
  "w-24",
  "w-20",
  "w-28",
  "w-24",
  "w-16",
];

const SkeletonBox = ({ className = "" }) => (
  <div className={`rounded-md bg-gray-200 ${className}`} />
);

/* ----------------------- Stats Cards ----------------------- */

const StatCardSkeleton = () => (
  <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
    <div className="flex flex-col gap-3">
      <SkeletonBox className="h-4 w-24" />
      <SkeletonBox className="h-8 w-16" />
      <SkeletonBox className="h-3 w-20" />
    </div>
  </div>
);

const StatsCardsSkeleton = () => (
  <div
    className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
    data-testid="stats-cards-skeleton"
  >
    {Array.from({ length: STAT_CARD_COUNT }, (_, index) => (
      <StatCardSkeleton key={`stat-card-${index}`} />
    ))}
  </div>
);

/* ----------------------- Candidate Table ----------------------- */

const TableHeaderSkeleton = () => (
  <thead className="border-b border-gray-200">
    <tr>
      {TABLE_COLUMN_WIDTHS.map((width, index) => (
        <th key={`header-${index}`} className="px-4 py-3 text-left">
          <SkeletonBox className={`h-4 ${width}`} />
        </th>
      ))}
    </tr>
  </thead>
);

const TableRowSkeleton = ({ row }) => (
  <tr key={row} className="border-b border-gray-100 last:border-none">
    {TABLE_COLUMN_WIDTHS.map((width, index) => (
      <td key={`${row}-${index}`} className="px-4 py-4">
        <SkeletonBox className={`h-4 ${width}`} />
      </td>
    ))}
  </tr>
);

const CandidateTableSkeleton = () => (
  <div
    className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm"
    data-testid="candidate-table-skeleton"
  >
    <table className="min-w-full">
      <TableHeaderSkeleton />

      <tbody>
        {Array.from({ length: TABLE_ROW_COUNT }, (_, index) => (
          <TableRowSkeleton key={`row-${index}`} row={index} />
        ))}
      </tbody>
    </table>
  </div>
);

/* ----------------------- Dashboard ----------------------- */

const DashboardSkeleton = () => {
  return (
    <div
      className="space-y-6 animate-pulse"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <span className="sr-only">Loading dashboard...</span>

      <StatsCardsSkeleton />

      <CandidateTableSkeleton />
    </div>
  );
};

export default React.memo(DashboardSkeleton);
