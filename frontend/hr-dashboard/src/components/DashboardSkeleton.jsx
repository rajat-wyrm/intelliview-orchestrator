import React from 'react';

/**
 * DashboardSkeleton.jsx
 *
 * Loading placeholder shown during initial dashboard load.
 * Mirrors the layout of:
 *  - StatsCards.jsx   (4 cards, single row on desktop)
 *  - CandidateTable.jsx (6-column table, 5 placeholder rows)
 *
 * Usage:
 *   {isInitialLoading ? <DashboardSkeleton /> : <DashboardContent data={data} />}
 *
 */

const SkeletonBox = ({ className = '' }) => (
  <div className={`bg-gray-200 rounded animate-pulse ${className}`} />
);

/* ---------- Stats cards skeleton (matches StatsCards.jsx) ---------- */

const StatCardSkeleton = () => (
  <div className="bg-white rounded-lg shadow p-6 flex flex-col gap-3">
    <SkeletonBox className="h-4 w-24" />   {/* label */}
    <SkeletonBox className="h-8 w-16" />   {/* big number */}
    <SkeletonBox className="h-3 w-20" />   {/* delta / subtext */}
  </div>
);

const StatsCardsSkeleton = () => (
  <div
    className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
    data-testid="stats-cards-skeleton"
  >
    {Array.from({ length: 4 }).map((_, i) => (
      <StatCardSkeleton key={i} />
    ))}
  </div>
);

/* ---------- Table skeleton (matches CandidateTable.jsx) ---------- */

const COLUMN_COUNT = 6;
const ROW_COUNT = 5;

const TableRowSkeleton = () => (
  <tr>
    {Array.from({ length: COLUMN_COUNT }).map((_, i) => (
      <td key={i} className="px-4 py-3">
        <SkeletonBox className="h-4 w-full" />
      </td>
    ))}
  </tr>
);

const CandidateTableSkeleton = () => (
  <div
    className="bg-white rounded-lg shadow overflow-hidden"
    data-testid="candidate-table-skeleton"
  >
    <table className="min-w-full divide-y divide-gray-200">
      <thead>
        <tr>
          {Array.from({ length: COLUMN_COUNT }).map((_, i) => (
            <th key={i} className="px-4 py-3 text-left">
              <SkeletonBox className="h-3 w-16" />
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {Array.from({ length: ROW_COUNT }).map((_, i) => (
          <TableRowSkeleton key={i} />
        ))}
      </tbody>
    </table>
  </div>
);

/* ---------- Full dashboard skeleton ---------- */

const DashboardSkeleton = () => {
  return (
    <div className="space-y-6" aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading dashboard…</span>
      <StatsCardsSkeleton />
      <CandidateTableSkeleton />
    </div>
  );
};

export default DashboardSkeleton;
