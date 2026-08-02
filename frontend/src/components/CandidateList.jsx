import React, { useState } from "react";

const riskStyles = {
  Low: "bg-green-100 text-green-800 border border-green-300",
  Medium: "bg-yellow-100 text-yellow-800 border border-yellow-300",
  High: "bg-red-100 text-red-800 border border-red-300",
};

function RiskBadge({ risk }) {
  return (
    <span
      className={`px-2 py-1 rounded-full text-xs font-medium ${
        riskStyles[risk] || "bg-gray-100 text-gray-800 border border-gray-300"
      }`}
    >
      {risk}
    </span>
  );
}

function CandidateModal({ candidate, onClose }) {
  if (!candidate) return null;
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-md p-6">
        <h2 className="text-lg font-semibold mb-4">{candidate.name}</h2>
        <div className="space-y-2 text-sm text-gray-700">
          <p><span className="font-medium">Domain:</span> {candidate.domain}</p>
          <p><span className="font-medium">Type:</span> {candidate.type}</p>
          <p><span className="font-medium">Score:</span> {candidate.score}/100</p>
          <p><span className="font-medium">Risk:</span> <RiskBadge risk={candidate.risk} /></p>
          <p><span className="font-medium">Status:</span> {candidate.status}</p>
        </div>
        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 rounded-md hover:bg-gray-300 text-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

function RescheduleModal({ candidate, onClose, onConfirm }) {
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");

  if (!candidate) return null;

  const handleConfirm = () => {
    console.log("Reschedule requested:", {
      candidateId: candidate.id,
      newDate: date,
      newTime: time,
    });
    onConfirm();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-sm p-6">
        <h2 className="text-lg font-semibold mb-4">
          Reschedule {candidate.name}
        </h2>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Date
            </label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Time
            </label>
            <input
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 rounded-md hover:bg-gray-300 text-sm"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!date || !time}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}

function CancelConfirmDialog({ candidate, onClose, onConfirm }) {
  if (!candidate) return null;
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-sm p-6">
        <h2 className="text-lg font-semibold mb-2">Cancel Interview?</h2>
        <p className="text-sm text-gray-600 mb-6">
          Are you sure you want to cancel the interview for{" "}
          <span className="font-medium">{candidate.name}</span>? This action
          cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 rounded-md hover:bg-gray-300 text-sm"
          >
            Keep
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm"
          >
            Cancel Interview
          </button>
        </div>
      </div>
    </div>
  );
}

export default function CandidateList({ candidates = [] }) {
  const [rows, setRows] = useState(candidates);
  const [viewCandidate, setViewCandidate] = useState(null);
  const [rescheduleCandidate, setRescheduleCandidate] = useState(null);
  const [cancelCandidate, setCancelCandidate] = useState(null);

  // Keep local rows in sync if parent passes new filtered data
  React.useEffect(() => {
    setRows(candidates);
  }, [candidates]);

  const handleCancelConfirm = () => {
    console.log("Cancel requested for candidate:", cancelCandidate.id);
    // Stub API call
    // await api.cancelInterview(cancelCandidate.id)
    setRows((prev) => prev.filter((c) => c.id !== cancelCandidate.id));
    setCancelCandidate(null);
  };

  return (
    <div className="w-full overflow-x-auto bg-white rounded-lg shadow border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Name</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Domain</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Type</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Score</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Risk</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.length === 0 ? (
            <tr>
              <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                No candidates found
              </td>
            </tr>
          ) : (
            rows.map((candidate) => (
              <tr key={candidate.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-800 font-medium">
                  {candidate.name}
                </td>
                <td className="px-4 py-3 text-gray-600">{candidate.domain}</td>
                <td className="px-4 py-3 text-gray-600">{candidate.type}</td>
                <td className="px-4 py-3 text-gray-600">
                  {candidate.score}/100
                </td>
                <td className="px-4 py-3">
                  <RiskBadge risk={candidate.risk} />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setViewCandidate(candidate)}
                      className="px-3 py-1 rounded-md bg-blue-50 text-blue-700 hover:bg-blue-100 text-xs font-medium"
                    >
                      View
                    </button>
                    {candidate.status === "scheduled" && (
                      <>
                        <button
                          onClick={() => setRescheduleCandidate(candidate)}
                          className="px-3 py-1 rounded-md bg-yellow-50 text-yellow-700 hover:bg-yellow-100 text-xs font-medium"
                        >
                          Reschedule
                        </button>
                        <button
                          onClick={() => setCancelCandidate(candidate)}
                          className="px-3 py-1 rounded-md bg-red-50 text-red-700 hover:bg-red-100 text-xs font-medium"
                        >
                          Cancel
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      <CandidateModal
        candidate={viewCandidate}
        onClose={() => setViewCandidate(null)}
      />

      <RescheduleModal
        candidate={rescheduleCandidate}
        onClose={() => setRescheduleCandidate(null)}
        onConfirm={() => setRescheduleCandidate(null)}
      />

      <CancelConfirmDialog
        candidate={cancelCandidate}
        onClose={() => setCancelCandidate(null)}
        onConfirm={handleCancelConfirm}
      />
    </div>
  );
}