"use client";
import { useState, useMemo } from "react";
import useSWR from "swr";
import {
  UserCircle,
  Search,
  BarChart3,
  Activity,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import Card from "@/components/Card";
import Stat from "@/components/Stat";
import StatsCards from "@/components/StatsCards";
import { StatusBadge, Badge } from "@/components/Badge";
import { Skeleton, ErrorState, EmptyState } from "@/components/States";
import { SearchInput } from "@/components/SearchInput";
import Pipeline from "@/components/Pipeline";
import { formatDate, formatRelative, riskColor, formatPercent } from "@/lib/utils";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function useCandidateData() {
  const completed = useSWR("/completed-sessions?limit=100", { refreshInterval: 10000 });
  const failed = useSWR("/failed-sessions?limit=100", { refreshInterval: 10000 });
  const active = useSWR("/active-sessions", { refreshInterval: 5000 });

  const candidates = useMemo(() => {
    const map = new Map();
    const allSessions = [
      ...(completed.data?.sessions ?? []),
      ...(failed.data?.sessions ?? []),
      ...(active.data?.sessions ?? []),
    ];

    for (const s of allSessions) {
      const id = s.candidate_id || "unknown";
      if (!map.has(id)) {
        map.set(id, {
          candidate_id: id,
          total_sessions: 0,
          completed_sessions: 0,
          failed_sessions: 0,
          active_sessions: 0,
          risk_scores: [],
          sessions: [],
        });
      }
      const c = map.get(id);
      c.total_sessions += 1;
      c.sessions.push(s);
      if (s.status === "COMPLETED") c.completed_sessions += 1;
      else if (s.status === "FAILED" || s.status === "TIMEOUT") c.failed_sessions += 1;
      else c.active_sessions += 1;
      if (s.risk_score != null) c.risk_scores.push(s.risk_score);
    }

    return Array.from(map.values())
      .map((c) => ({
        ...c,
        avg_risk_score:
          c.risk_scores.length > 0
            ? c.risk_scores.reduce((a, b) => a + b, 0) / c.risk_scores.length
            : null,
        latest_session: c.sessions.sort(
          (a, b) => new Date(b.updated_at || 0) - new Date(a.updated_at || 0)
        )[0],
      }))
      .sort((a, b) => b.total_sessions - a.total_sessions);
  }, [completed.data, failed.data, active.data]);

  return {
    candidates,
    isLoading: completed.isLoading && failed.isLoading,
    error: completed.error || failed.error,
    mutate: () => {
      completed.mutate();
      failed.mutate();
      active.mutate();
    },
  };
}

export default function CandidatesPage() {
  const { candidates, isLoading, error, mutate } = useCandidateData();
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState(null);

  const filtered = useMemo(() => {
    if (!search.trim()) return candidates;
    const q = search.toLowerCase();
    return candidates.filter((c) => c.candidate_id.toLowerCase().includes(q));
  }, [candidates, search]);

  const selected = candidates.find((c) => c.candidate_id === selectedId);

  const statusData = useMemo(() => {
    if (!selected) return [];
    const counts = {};
    for (const s of selected.sessions) {
      counts[s.status] = (counts[s.status] || 0) + 1;
    }
    return Object.entries(counts).map(([status, count]) => ({ status, count }));
  }, [selected]);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">Candidates</h1>
          <p className="text-sm text-muted">Candidate profiles, interview history, and performance analytics.</p>
        </div>
        <div className="text-xs text-muted">
          {candidates.length} candidates
        </div>
      </div>

      <StatsCards
        data={{
          totalCandidates: candidates.length,
          pendingReview: candidates.reduce((a, c) => a + c.active_sessions, 0),
          completed: candidates.reduce((a, c) => a + c.completed_sessions, 0),
          activeNow: candidates.filter((c) => c.active_sessions > 0).length,
        }}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <Card
            title="Candidate List"
            description={`${filtered.length} candidates`}
            action={
              <SearchInput
                value={search}
                onChange={setSearch}
                placeholder="Search candidates..."
                className="w-48"
              />
            }
          >
            {error ? (
              <ErrorState error={error} onRetry={mutate} />
            ) : isLoading ? (
              <Skeleton className="h-48 w-full" />
            ) : filtered.length === 0 ? (
              <EmptyState
                title="No candidates"
                description="Candidate data will appear after sessions are completed."
              />
            ) : (
              <div className="max-h-[500px] space-y-1 overflow-y-auto">
                {filtered.map((c) => (
                  <button
                    key={c.candidate_id}
                    onClick={() => setSelectedId(c.candidate_id)}
                    className={cn(
                      "flex w-full items-center justify-between rounded-md px-3 py-2.5 text-left text-sm transition-colors",
                      selectedId === c.candidate_id
                        ? "bg-accent/15 text-accent-light"
                        : "text-zinc-300 hover:bg-bg-card"
                    )}
                  >
                    <div className="min-w-0">
                      <div className="truncate font-mono text-xs text-zinc-200">
                        {c.candidate_id}
                      </div>
                      <div className="text-[10px] text-muted">
                        {c.total_sessions} session{c.total_sessions !== 1 ? "s" : ""}
                      </div>
                    </div>
                    {c.avg_risk_score != null && (
                      <Badge variant={riskColor(c.avg_risk_score)}>
                        {c.avg_risk_score.toFixed(2)}
                      </Badge>
                    )}
                  </button>
                ))}
              </div>
            )}
          </Card>
        </div>

        <div className="lg:col-span-2">
          {!selected ? (
            <Card>
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <UserCircle size={48} className="mb-3 text-muted opacity-30" />
                <p className="text-sm text-zinc-300">Select a candidate to view details</p>
                <p className="mt-1 text-xs text-muted">
                  Click on a candidate from the list to see their profile
                </p>
              </div>
            </Card>
          ) : (
            <div className="space-y-4">
              <Card title={selected.candidate_id} description="Candidate profile and performance">
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <div className="rounded-md border border-border bg-bg-card px-3 py-2.5">
                    <div className="text-[10px] uppercase tracking-wide text-muted">Total</div>
                    <div className="mt-1 text-lg font-semibold text-zinc-50">
                      {selected.total_sessions}
                    </div>
                  </div>
                  <div className="rounded-md border border-border bg-bg-card px-3 py-2.5">
                    <div className="text-[10px] uppercase tracking-wide text-muted">Completed</div>
                    <div className="mt-1 text-lg font-semibold text-emerald-400">
                      {selected.completed_sessions}
                    </div>
                  </div>
                  <div className="rounded-md border border-border bg-bg-card px-3 py-2.5">
                    <div className="text-[10px] uppercase tracking-wide text-muted">Failed</div>
                    <div className="mt-1 text-lg font-semibold text-rose-400">
                      {selected.failed_sessions}
                    </div>
                  </div>
                  <div className="rounded-md border border-border bg-bg-card px-3 py-2.5">
                    <div className="text-[10px] uppercase tracking-wide text-muted">Avg Risk</div>
                    <div className="mt-1 text-lg font-semibold text-zinc-50">
                      {selected.avg_risk_score != null ? selected.avg_risk_score.toFixed(3) : "—"}
                    </div>
                  </div>
                </div>
              </Card>

              {statusData.length > 0 && (
                <Card title="Session Status Distribution">
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={statusData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                      <XAxis dataKey="status" stroke="#71717a" fontSize={11} />
                      <YAxis stroke="#71717a" fontSize={11} />
                      <Tooltip
                        contentStyle={{
                          background: "#12121a",
                          border: "1px solid #27272a",
                          borderRadius: 8,
                        }}
                      />
                      <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              )}

              <Card title="Interview History" description="All sessions for this candidate">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="text-left text-xs uppercase tracking-wide text-muted">
                      <tr>
                        <th className="py-2 pr-4">Session</th>
                        <th className="py-2 pr-4">Pipeline</th>
                        <th className="py-2 pr-4">Status</th>
                        <th className="py-2 pr-4">Risk</th>
                        <th className="py-2 pr-4">Worker</th>
                        <th className="py-2 pr-4">Updated</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selected.sessions
                        .sort(
                          (a, b) =>
                            new Date(b.updated_at || 0) - new Date(a.updated_at || 0)
                        )
                        .map((s) => (
                          <tr key={s.session_id} className="border-t border-border">
                            <td className="py-2 pr-4 font-mono text-xs text-zinc-300">
                              {s.session_id}
                            </td>
                            <td className="py-2 pr-4">
                              <Pipeline current={s.status} />
                            </td>
                            <td className="py-2 pr-4">
                              <StatusBadge status={s.status} />
                            </td>
                            <td className="py-2 pr-4">
                              {s.risk_score != null ? (
                                <Badge variant={riskColor(s.risk_score)}>
                                  {s.risk_score.toFixed(2)}
                                </Badge>
                              ) : (
                                <span className="text-muted">—</span>
                              )}
                            </td>
                            <td className="py-2 pr-4 font-mono text-xs text-muted">
                              {s.assigned_node ?? "—"}
                            </td>
                            <td className="py-2 pr-4 text-muted">
                              {formatDate(s.updated_at ?? s.end_time)}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
