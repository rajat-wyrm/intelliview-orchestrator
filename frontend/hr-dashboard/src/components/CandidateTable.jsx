import React from "react";

function CandidateTable({ candidates }) {
  if (!candidates || candidates.length === 0) {
    return <p>No candidates found.</p>;
  }

  return (
    <table className="candidate-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Domain</th>
          <th>Type</th>
          <th>Status</th>
          <th>Applied Date</th>
        </tr>
      </thead>
      <tbody>
        {candidates.map((candidate) => (
          <tr key={candidate.id}>
            <td>{candidate.name}</td>
            <td>{candidate.domain}</td>
            <td>{candidate.type}</td>
            <td>{candidate.status}</td>
            <td>{candidate.appliedDate}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default CandidateTable;