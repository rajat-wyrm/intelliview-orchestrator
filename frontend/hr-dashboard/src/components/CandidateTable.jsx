"use client";
import { Badge } from "@/components/Badge";
import { EmptyState } from "@/components/States";

const statusVariant = {
  pending: "warn",
  selected: "success",
  rejected: "danger",
};

function CandidateTable({ candidates }) {
  if (!candidates || candidates.length === 0) {
    return (
      <EmptyState
        title="No candidates found"
        description="Try adjusting your filters."
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-bg-panel">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
            <th className="px-4 py-3 font-medium">Name</th>
            <th className="px-4 py-3 font-medium">Domain</th>
            <th className="px-4 py-3 font-medium">Type</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Applied Date</th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((candidate) => (
            <tr
              key={candidate.id}
              className="border-b border-border last:border-0 hover:bg-bg-card"
            >
              <td className="px-4 py-3 text-zinc-100">{candidate.name}</td>
              <td className="px-4 py-3 text-muted capitalize">{candidate.domain}</td>
              <td className="px-4 py-3 text-muted capitalize">{candidate.type}</td>
              <td className="px-4 py-3">
                <Badge variant={statusVariant[candidate.status] || "muted"}>
  {candidate.status}
</Badge> 
              </td>
              <td className="px-4 py-3 text-muted">{candidate.appliedDate}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default CandidateTable;
