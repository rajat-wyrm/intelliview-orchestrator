"use client";
import { useMemo, useState } from "react";
import useSWR from "swr";
import {
  Sparkles,
  ThumbsUp,
  ThumbsDown,
  Lightbulb,
  MessageSquare,
  TrendingUp,
  Hash,
} from "lucide-react";
import Card from "@/components/Card";
import Stat from "@/components/Stat";
import { Badge } from "@/components/Badge";
import { Skeleton, ErrorState, EmptyState } from "@/components/States";
import { Button, Input } from "@/components/ui";
import Sparkline from "@/components/Sparkline";
import { useAppStore } from "@/lib/store";
import { formatDate, riskColor } from "@/lib/utils";
import { normalizeCoachingData, buildScoreTrend } from "@/lib/coaching";

/**
 * CoachingReport — candidate-facing coaching experience for a single
 * interview session. Reuses the existing report/session data structures
 * (see lib/coaching.js) and the shared Card/Stat/Badge/States primitives
 * already used throughout the dashboard.
 */
function CoachingReport({ sessionId }) {
  const token = useAppStore((s) => s.token);

  const {
    data: report,
    error: reportError,
    isLoading: reportLoading,
    mutate: retryReport,
  } = useSWR(sessionId && token ? `/interviews/${sessionId}/report` : null);

  const candidateId = report?.candidate?.candidate_id ?? null;

  const { data: historyData } = useSWR(
    candidateId && token ? `/candidates/${candidateId}/history` : null,
  );

  const coaching = useMemo(() => normalizeCoachingData(report), [report]);
  const trend = useMemo(() => buildScoreTrend(historyData?.history), [historyData]);

  if (!sessionId) {
    return <NoSessionSelected />;
  }

  if (reportError) {
    return (
      <div data-testid="coaching-error">
        <ErrorState error={reportError} onRetry={() => retryReport()} />
      </div>
    );
  }

  if (reportLoading && !report) {
    return (
      <div data-testid="coaching-loading" className="space-y-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (!coaching || !coaching.hasCoachingContent) {
    return (
      <div data-testid="coaching-empty">
        <EmptyState
          title="Coaching feedback isn't available yet"
          description="Check back after this interview has finished processing."
        />
      </div>
    );
  }

  return (
    <div data-testid="coaching-report" className="space-y-6">
      <CoachingHeader coaching={coaching} />
      <OverallPerformance coaching={coaching} />
      <div className="grid gap-4 md:grid-cols-2">
        <StrengthsWeaknesses coaching={coaching} />
        <CoachingFeedback coaching={coaching} />
      </div>
      <QuestionBreakdown coaching={coaching} />
      <PerformanceOverTime trend={trend} />
    </div>
  );
}

function NoSessionSelected() {
  const [value, setValue] = useState("");
  return (
    <div data-testid="coaching-missing-session" className="flex flex-col items-center">
      <EmptyState
        title="No session selected"
        description="Enter an interview session ID to view its coaching report."
      />
      <form
        className="mt-4 flex w-full max-w-sm items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (value.trim() && typeof window !== "undefined") {
            window.location.search = `?session=${encodeURIComponent(value.trim())}`;
          }
        }}
      >
        <Input
          aria-label="Session ID"
          placeholder="session id"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
        <Button type="submit" variant="primary" size="md" disabled={!value.trim()}>
          View
        </Button>
      </form>
    </div>
  );
}

function CoachingHeader({ coaching }) {
  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-accent/15 text-accent-light">
            <Sparkles size={18} />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-zinc-50">
              {coaching.candidate?.name ?? "Your coaching report"}
            </h1>
            <p className="flex items-center gap-1.5 text-xs text-muted">
              <Hash size={11} />
              <span className="font-mono">{coaching.sessionId}</span>
            </p>
          </div>
        </div>
        {coaching.recommendation && (
          <Badge variant={coaching.recommendation === "progress" ? "success" : "warn"}>
            {coaching.recommendation.replace(/_/g, " ")}
          </Badge>
        )}
      </div>
      {coaching.summary && (
        <div className="mt-4 flex flex-wrap gap-4 text-xs text-muted">
          {coaching.summary.start_time && (
            <span>Interviewed on {formatDate(coaching.summary.start_time)}</span>
          )}
          {coaching.summary.duration_minutes != null && (
            <span>{coaching.summary.duration_minutes} min</span>
          )}
        </div>
      )}
    </Card>
  );
}

function OverallPerformance({ coaching }) {
  if (!coaching.overall && !coaching.risk) return null;
  return (
    <div>
      <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">
        Overall performance
      </h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {coaching.overall?.quality != null && (
          <Stat label="Quality" value={coaching.overall.quality.toFixed(1)} />
        )}
        {coaching.overall?.accuracy != null && (
          <Stat label="Accuracy" value={coaching.overall.accuracy.toFixed(1)} />
        )}
        {coaching.overall?.clarity != null && (
          <Stat label="Clarity" value={coaching.overall.clarity.toFixed(1)} />
        )}
        {coaching.risk?.classification && (
          <Stat
            label="Risk"
            value={
              <Badge variant={riskColor(coaching.risk.score)}>
                {coaching.risk.classification}
              </Badge>
            }
          />
        )}
      </div>
    </div>
  );
}

function StrengthsWeaknesses({ coaching }) {
  return (
    <div className="space-y-4">
      <div data-testid="coaching-strengths">
        <Card title="Strengths">
          {coaching.strengths.length > 0 ? (
            <ul className="space-y-2">
              {coaching.strengths.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-zinc-300">
                  <ThumbsUp size={14} className="mt-0.5 shrink-0 text-emerald-400" />
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted">No strengths recorded for this interview.</p>
          )}
        </Card>
      </div>
      <div data-testid="coaching-weaknesses">
        <Card title="Areas to improve">
          {coaching.improvements.length > 0 ? (
            <ul className="space-y-2">
              {coaching.improvements.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-zinc-300">
                  <ThumbsDown size={14} className="mt-0.5 shrink-0 text-amber-400" />
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted">No improvement areas recorded for this interview.</p>
          )}
        </Card>
      </div>
    </div>
  );
}

function CoachingFeedback({ coaching }) {
  return (
    <div data-testid="coaching-feedback">
      <Card title="Coaching feedback">
        {coaching.detailedFeedback ? (
          <div className="flex items-start gap-2">
            <MessageSquare size={14} className="mt-0.5 shrink-0 text-accent-light" />
            <p className="text-sm text-zinc-300">{coaching.detailedFeedback}</p>
          </div>
        ) : (
          <p className="text-sm text-muted">Detailed coaching feedback isn't available yet.</p>
        )}
        {coaching.improvements.length > 0 && (
          <div className="mt-4 flex items-start gap-2 rounded-md border border-border bg-bg-card px-3 py-2.5">
            <Lightbulb size={14} className="mt-0.5 shrink-0 text-amber-400" />
            <p className="text-xs text-muted">
              Focus on: {coaching.improvements.slice(0, 2).join("; ")}
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}

function QuestionBreakdown({ coaching }) {
  if (coaching.questions.length === 0) return null;
  return (
    <div data-testid="coaching-questions">
      <Card
        title="Question-by-question"
        description="Sample answers appear where the interview generated one."
      >
        <div className="space-y-4">
          {coaching.questions.map((q, i) => (
            <div key={q.id ?? i} className="rounded-md border border-border bg-bg-card p-3">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm font-medium text-zinc-100">{q.text}</p>
                {q.score != null && <Badge variant="accent">{q.score.toFixed(1)}</Badge>}
              </div>
              {q.answer && <p className="mt-2 text-sm text-zinc-400">{q.answer}</p>}
              {q.feedback && (
                <p className="mt-2 text-xs text-muted">
                  <span className="font-medium text-zinc-300">Feedback: </span>
                  {q.feedback}
                </p>
              )}
              {q.sampleAnswer && (
                <p className="mt-2 text-xs text-emerald-300/90">
                  <span className="font-medium">Sample answer: </span>
                  {q.sampleAnswer}
                </p>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function PerformanceOverTime({ trend }) {
  if (trend.length === 0) return null;
  const values = trend.map((t) => t.score);
  const latest = values[values.length - 1];
  const first = values[0];
  const delta = latest - first;
  return (
    <div data-testid="coaching-history">
      <Card title="Performance over time">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-1.5 text-xs text-muted">
              <TrendingUp size={12} />
              <span>Across {trend.length} completed interviews</span>
            </div>
            <div className="mt-1 text-2xl font-semibold text-zinc-50">
              {latest.toFixed(1)}
            </div>
            <div className={`mt-0.5 text-xs ${delta >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
              {delta >= 0 ? "+" : ""}
              {delta.toFixed(1)} since first session
            </div>
          </div>
          <Sparkline data={values} color="#6366f1" />
        </div>
      </Card>
    </div>
  );
}

export default CoachingReport;
export { NoSessionSelected };