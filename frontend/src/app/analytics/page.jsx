"use client";


import { useMemo, useState, useCallback } from "react";
import useSWR from "swr";
import MetricsDashboard from "@/components/analytics/MetricsDashboard";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  PieChart,
  Pie,
  Cell,
  Legend,
  Line,
  LineChart,
} from "recharts";
import { Download, Calendar, TrendingUp, Filter } from "lucide-react";
import Card from "@/components/Card";
import Stat from "@/components/Stat";
import { Badge } from "@/components/Badge";
import { Skeleton, ErrorState } from "@/components/States";
import { endpoints } from "@/lib/api";
import { toast } from "@/lib/toast";
import { cn } from "@/lib/utils";
import { ErrorBoundary } from "@/components/ErrorBoundary";

const RISK_BUCKETS = [
  { name: "Low (<0.3)", color: "#10b981" },
  { name: "Medium (0.3-0.6)", color: "#f59e0b" },
  { name: "High (0.6-0.8)", color: "#f97316" },
  { name: "Critical (≥0.8)", color: "#ef4444" },
];

const DATE_PRESETS = [
  { label: "All time", value: "all" },
  { label: "Last 24h", value: "24h" },
  { label: "Last 7d", value: "7d" },
  { label: "Last 30d", value: "30d" },
];

const TOOLTIP_STYLE = {
  contentStyle: { background: "#12121a", border: "1px solid #27272a", borderRadius: 8 },
};

function filterByDate(sessions, range) {
  if (range === "all") return sessions;
  const now = Date.now();
  const ms = { "24h": 86400000, "7d": 604800000, "30d": 2592000000 }[range];
  return sessions.filter((s) => {
    const t = new Date(s.updated_at || s.created_at || 0).getTime();
    return now - t <= ms;
  });
}

function RiskDistribution({ sessions, loading, onDrillDown }) {
  const buckets = useMemo(() => {
    const counts = RISK_BUCKETS.map((b) => ({ ...b, value: 0 }));
    for (const s of sessions) {
      const r = s?.risk_score;
      if (typeof r !== "number") continue;
      if (r < 0.3) counts[0].value += 1;
      else if (r < 0.6) counts[1].value += 1;
      else if (r < 0.8) counts[2].value += 1;
      else counts[3].value += 1;
    }
    return counts;
  }, [sessions]);

  return (
    <Card
      title="Risk distribution"
      description="Sessions bucketed by final risk score."
      action={
        <button
          onClick={() => onDrillDown("risk")}
          className="flex items-center gap-1 rounded-md border border-border bg-bg-card px-2 py-1 text-xs text-muted hover:text-zinc-200"
        >
          <Filter size={12} /> Drill down
        </button>
      }
    >
      {loading ? (
        <Skeleton className="h-64 w-full" />
      ) : buckets.every((b) => b.value === 0) ? (
        <div className="py-8 text-center text-sm text-muted">No sessions with risk scores yet.</div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={buckets}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={90}
              innerRadius={50}
              paddingAngle={2}
            >
              {buckets.map((b, i) => (
                <Cell key={i} fill={b.color} />
              ))}
            </Pie>
            <Tooltip {...TOOLTIP_STYLE} />
            <Legend wrapperStyle={{ fontSize: 12, color: "#a1a1aa" }} />
          </PieChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}

function TrendChart({ sessions }) {
  const trendData = useMemo(() => {
    const byDate = {};
    for (const s of sessions) {
      const date = (s.updated_at || s.created_at || "").slice(0, 10);
      if (!date) continue;
      if (!byDate[date]) byDate[date] = { date, completed: 0, failed: 0, avgRisk: 0, riskCount: 0 };
      if (s.status === "COMPLETED") byDate[date].completed += 1;
      else if (s.status === "FAILED" || s.status === "TIMEOUT") byDate[date].failed += 1;
      if (s.risk_score != null) {
        byDate[date].avgRisk += s.risk_score;
        byDate[date].riskCount += 1;
      }
    }
    return Object.values(byDate)
      .map((d) => ({
        ...d,
        avgRisk: d.riskCount > 0 ? d.avgRisk / d.riskCount : null,
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [sessions]);

  return (
    <Card title="Trend analysis" description="Daily session completion and failure trends.">
      {trendData.length === 0 ? (
        <div className="py-8 text-center text-sm text-muted">No data for trend analysis.</div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis dataKey="date" stroke="#71717a" fontSize={11} />
            <YAxis stroke="#71717a" fontSize={11} />
            <Tooltip {...TOOLTIP_STYLE} />
            <Legend wrapperStyle={{ fontSize: 12, color: "#a1a1aa" }} />
            <Line
              type="monotone"
              dataKey="completed"
              stroke="#10b981"
              strokeWidth={2}
              dot={{ r: 3 }}
              name="Completed"
            />
            <Line
              type="monotone"
              dataKey="failed"
              stroke="#ef4444"
              strokeWidth={2}
              dot={{ r: 3 }}
              name="Failed"
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}

function DrillDownModal({ type, sessions, onClose }) {
  const data = useMemo(() => {
    if (type === "risk") {
      return sessions
        .filter((s) => s.risk_score != null)
        .sort((a, b) => b.risk_score - a.risk_score)
        .map((s) => ({
          session_id: s.session_id,
          candidate_id: s.candidate_id,
          risk_score: s.risk_score,
          status: s.status,
        }));
    }
    return [];
  }, [type, sessions]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-xl border border-border bg-bg-panel shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h3 className="text-sm font-semibold text-zinc-100">
            {type === "risk" ? "Risk Score Breakdown" : "Drill Down"}
          </h3>
          <button
            onClick={onClose}
            className="rounded-md border border-border bg-bg-card px-2 py-1 text-xs text-muted hover:text-zinc-200"
          >
            Close
          </button>
        </div>
        <div className="max-h-[60vh] overflow-y-auto p-5">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="py-2 pr-4">Session</th>
                <th className="py-2 pr-4">Candidate</th>
                <th className="py-2 pr-4">Risk Score</th>
                <th className="py-2 pr-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.map((s) => (
                <tr key={s.session_id} className="border-t border-border">
                  <td className="py-2 pr-4 font-mono text-xs text-zinc-300">{s.session_id}</td>
                  <td className="py-2 pr-4 text-zinc-300">{s.candidate_id}</td>
                  <td className="py-2 pr-4">
                    <Badge
                      variant={
                        s.risk_score >= 0.8
                          ? "danger"
                          : s.risk_score >= 0.6
                            ? "warn"
                            : "success"
                      }
                    >
                      {s.risk_score.toFixed(3)}
                    </Badge>
                  </td>
                  <td className="py-2 pr-4 text-zinc-300">{s.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const stats = useSWR("/session-statistics", { refreshInterval: 10000 });
  const faults = useSWR("/fault-statistics", { refreshInterval: 10000 });
  const dlq = useSWR("/dead-letter-queue?limit=50", { refreshInterval: 10000 });
  const completed = useSWR("/completed-sessions?limit=100", { refreshInterval: 10000 });
  const failed = useSWR("/failed-sessions?limit=100", { refreshInterval: 10000 });

  const [dateRange, setDateRange] = useState("all");
  const [drillDown, setDrillDown] = useState(null);

  const allSessions = useMemo(
    () => [...(completed.data?.sessions ?? []), ...(failed.data?.sessions ?? [])],
    [completed.data, failed.data]
  );

  const filteredSessions = useMemo(() => filterByDate(allSessions, dateRange), [allSessions, dateRange]);

  const breakdown = useMemo(() => {
    if (!stats.data) return [];
    return Object.entries(stats.data.status_breakdown).map(([status, count]) => ({
      status,
      count,
    }));
  }, [stats.data]);

  const failureData = useMemo(() => {
    if (!faults.data) return [];
    return Object.entries(faults.data.fault_statistics.failures_by_type).map(
      ([type, count]) => ({ type, count })
    );
  }, [faults.data]);

  const handleExport = useCallback(() => {
    const csv = [
      "session_id,candidate_id,status,risk_score,worker,updated_at",
      ...filteredSessions.map(
        (s) =>
          `${s.session_id},${s.candidate_id || ""},${s.status},${s.risk_score ?? ""},${s.assigned_node || ""},${s.updated_at || ""}`
      ),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `analytics-export-${dateRange}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Export complete", "CSV file downloaded");
  }, [filteredSessions, dateRange]);

  return (
    <ErrorBoundary>
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-zinc-50">Analytics</h1>
            <p className="text-sm text-muted">Risk distribution, failure modes, trends, and export.</p>
          </div>
          <button
            onClick={handleExport}
            className="flex items-center gap-1.5 rounded-md border border-border bg-bg-card px-3 py-1.5 text-xs text-muted hover:text-zinc-200"
          >
            <Download size={14} /> Export CSV
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Calendar size={14} className="text-muted" />
          {DATE_PRESETS.map((p) => (
            <button
              key={p.value}
              onClick={() => setDateRange(p.value)}
              className={cn(
                "rounded-md px-3 py-1.5 text-xs font-medium",
                dateRange === p.value
                  ? "bg-accent/15 text-accent-light"
                  : "text-muted hover:bg-bg-card hover:text-zinc-200"
              )}
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat
            label="Total sessions"
            value={stats.data?.total_sessions ?? <Skeleton className="h-7 w-12" />}
          />
          <Stat
            label="Avg risk"
            value={
              stats.data ? (
                stats.data.risk_score_stats.average_risk_score.toFixed(3)
              ) : (
                <Skeleton className="h-7 w-16" />
              )
            }
          />
          <Stat
            label="High risk"
            value={
              stats.data?.risk_score_stats.high_risk_sessions ?? (
                <Skeleton className="h-7 w-12" />
              )
            }
          />
          <Stat
            label="DLQ size"
            value={dlq.data?.count ?? <Skeleton className="h-7 w-12" />}
          />
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card title="Sessions by status" description="Distribution across the lifecycle states.">
            {stats.error ? (
              <ErrorState error={stats.error} onRetry={() => stats.mutate()} />
            ) : !stats.data ? (
              <Skeleton className="h-64 w-full" />
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={breakdown}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="status" stroke="#71717a" fontSize={11} />
                  <YAxis stroke="#71717a" fontSize={11} />
                  <Tooltip {...TOOLTIP_STYLE} />
                  <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>

          <Card title="Failure breakdown" description="Counts grouped by failure type.">
            {faults.error ? (
              <ErrorState error={faults.error} onRetry={() => faults.mutate()} />
            ) : !faults.data ? (
              <Skeleton className="h-64 w-full" />
            ) : failureData.length === 0 ? (
              <div className="py-8 text-center text-sm text-muted">No failures recorded.</div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={failureData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="type" stroke="#71717a" fontSize={11} />
                  <YAxis stroke="#71717a" fontSize={11} />
                  <Tooltip {...TOOLTIP_STYLE} />
                  <Bar dataKey="count" fill="#ef4444" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <RiskDistribution
            sessions={filteredSessions}
            loading={completed.isLoading && failed.isLoading}
            onDrillDown={(type) => setDrillDown(type)}
          />
          <TrendChart sessions={filteredSessions} />
        </div>

        {drillDown && (
          <DrillDownModal
            type={drillDown}
            sessions={filteredSessions}
            onClose={() => setDrillDown(null)}
          />
        )}
</div>

      <div className="border-t border-border pt-6">
        <MetricsDashboard />
      </div>
    </ErrorBoundary>
  );
}
