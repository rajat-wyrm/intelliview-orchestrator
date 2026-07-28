"use client";

import Card from "@/components/Card";
import { Activity } from "lucide-react";

export default function RiskTimeline({ moments = [] }) {
  const sortedMoments = [...moments].sort(
    (a, b) => (a.startTime || 0) - (b.startTime || 0)
  );

  const getColor = (type) => {
    switch (type) {
      case "session_start":
        return "bg-emerald-500";
      case "question_asked":
        return "bg-blue-500";
      case "answer_received":
        return "bg-purple-500";
      case "risk_detected":
        return "bg-red-500";
      case "ai_feedback":
        return "bg-amber-500";
      case "recording_start":
        return "bg-cyan-500";
      case "recording_stop":
      case "session_end":
        return "bg-zinc-500";
      default:
        return "bg-zinc-500";
    }
  };

  const getLabel = (type) => {
    switch (type) {
      case "session_start":
        return "Interview Started";
      case "question_asked":
        return "Question Asked";
      case "answer_received":
        return "Answer Received";
      case "risk_detected":
        return "Risk Detected";
      case "ai_feedback":
        return "AI Feedback";
      case "recording_start":
        return "Recording Started";
      case "recording_stop":
        return "Recording Stopped";
      case "session_end":
        return "Interview Ended";
      default:
        return type.replace(/_/g, " ");
    }
  };

  // Actual clock time
  const formatClock = (timestamp) => {
    if (!timestamp) return "--";

    return new Date(timestamp).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  // Timeline timestamp (00:00, 00:15...)
  const formatTimeline = (timestamp) => {
    if (!timestamp || sortedMoments.length === 0) return "00:00";

    const elapsed = Math.floor(
      (timestamp - sortedMoments[0].startTime) / 1000
    );

    const minutes = Math.floor(elapsed / 60)
      .toString()
      .padStart(2, "0");

    const seconds = (elapsed % 60)
      .toString()
      .padStart(2, "0");

    return `${minutes}:${seconds}`;
  };

  const totalDuration =
    sortedMoments.length > 1
      ? (sortedMoments[sortedMoments.length - 1].endTime ||
          sortedMoments[sortedMoments.length - 1].startTime) -
        sortedMoments[0].startTime
      : 1;

  return (
    <Card
      title="Risk Timeline"
      description="Chronological interview events"
    >
      {sortedMoments.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <Activity
            size={42}
            className="mb-3 text-muted opacity-40"
          />

          <p className="text-sm text-zinc-300">
            No interview events yet
          </p>

          <p className="mt-1 max-w-xs text-xs text-muted">
            Timeline events will automatically appear after the interview
            starts and AI begins detecting activities.
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {/* Timeline Bar */}
          <div>
            <div className="mb-2 flex items-center justify-between text-xs text-muted">
              <span>Timeline</span>
              <span>
                {Math.floor(totalDuration / 60000)}m{" "}
                {Math.floor((totalDuration % 60000) / 1000)}s
              </span>
            </div>

            <div className="relative h-2 rounded-full bg-zinc-800 overflow-hidden">
              {sortedMoments.map((moment, index) => {
                const left =
                  ((moment.startTime - sortedMoments[0].startTime) /
                    totalDuration) *
                  100;

                return (
                  <div
                    key={moment.id || index}
                    className={`absolute h-full w-2 rounded-full ${getColor(
                      moment.type
                    )}`}
                    style={{
                      left: `${Math.min(left, 98)}%`,
                    }}
                  />
                );
              })}
            </div>
          </div>

          {/* Event List */}
          {sortedMoments.map((moment, index) => (
            <div
              key={moment.id || index}
              className="flex items-start gap-3"
            >
              <div className="flex flex-col items-center">
                <div
                  className={`h-3 w-3 rounded-full ${getColor(
                    moment.type
                  )}`}
                />

                {index !== sortedMoments.length - 1 && (
                  <div className="mt-1 h-12 w-px bg-border" />
                )}
              </div>

              <div className="flex-1 rounded-md border border-border bg-bg-card px-3 py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-zinc-100">
                      {getLabel(moment.type)}
                    </span>

                    {moment.type === "risk_detected" && (
                      <span className="rounded bg-red-500/20 px-2 py-0.5 text-[10px] font-semibold text-red-400">
                        Critical
                      </span>
                    )}
                  </div>

                  <div className="text-right text-xs text-muted">
                    <div>{formatTimeline(moment.startTime)}</div>
                    <div>{formatClock(moment.startTime)}</div>
                  </div>
                </div>

                {moment.metadata &&
                  Object.keys(moment.metadata).length > 0 && (
                    <div className="mt-3 text-xs text-muted">
                      {Object.entries(moment.metadata).map(([key, value]) => (
                        <div key={key}>
                          <span className="font-medium">{key}:</span>{" "}
                          {String(value)}
                        </div>
                      ))}
                    </div>
                  )}

                {moment.data &&
                  Object.keys(moment.data).length > 0 && (
                    <div className="mt-3 text-xs text-muted">
                      {Object.entries(moment.data).map(([key, value]) => (
                        <div key={key}>
                          <span className="font-medium">{key}:</span>{" "}
                          {String(value)}
                        </div>
                      ))}
                    </div>
                  )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
