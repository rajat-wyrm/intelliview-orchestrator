"use client";
import { useEffect, useState, useMemo } from "react";
import useSWR from "swr";
import { Activity, AlertTriangle, CheckCircle2, Users, Zap, Shield, TrendingUp, Clock } from "lucide-react";
import Card from "@/components/Card";
import Stat from "@/components/Stat";
import { StatusBadge } from "@/components/Badge";
import { Skeleton, ErrorState, EmptyState } from "@/components/States";
import Sparkline from "@/components/Sparkline";
import { formatPercent, formatRelative } from "@/lib/utils";

const MAX_SAMPLES = 20;

export default function OverviewPage() {
  const health = useSWR("/system-health", { refreshInterval: 3000 });
  const workers = useSWR("/workers", { refreshInterval: 5000 });
  const stats = useSWR("/session-statistics", { refreshInterval: 5000 });
  const active = useSWR("/active-sessions", { refreshInterval: 3000 });

  const [completedHist, setCompletedHist] = useState([]);
  const [failedHist, setFailedHist] = useState([]);
  const [riskHist, setRiskHist] = useState([]);

  const completed = stats.data?.completed_sessions;
  const failed = stats.data?.failed_sessions;
  const avgRisk = stats.data?.risk_score_stats?.average_risk_score;

  useEffect(() => {
    if (completed == null) return;
    setCompletedHist((h) => [...h, completed].slice(-MAX_SAMPLES));
  }, [completed]);
  useEffect(() => {
    if (failed == null) return;
    setFailedHist((h) => [...h, failed].slice(-MAX_SAMPLES));
  }, [failed]);
  useEffect(() => {
    if (avgRisk == null) return;
    setRiskHist((h) => [...h, avgRisk].slice(-MAX_SAMPLES));
  }, [avgRisk]);

  const utilization = useMemo(() => {
    const list = workers.data?.workers ?? [];
    if (list.length === 0) return 0;
    const total = list.reduce((acc, w) => acc + (w.capacity ? (w.active_tasks / w.capacity) * 100 : 0), 0);
    return total / list.length;
  }, [workers.data?.workers]);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">Overview</h1>
          <p className="text-sm text-muted">Real-time system health and throughput.</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs text-muted">Live</span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="glass-card p-4 animate-slide-in-up" style={{ animationDelay: "0ms" }}>
          <Stat
            label="System"
            value={health.data ? <StatusBadge status={health.data.overall_status} /> : <Skeleton className="h-7 w-20" />}
            hint={health.data ? `Updated ${formatRelative(health.data.timestamp)}` : ""}
            icon={<Activity size={16} />}
          />
        </div>
        <div className="glass-card p-4 animate-slide-in-up" style={{ animationDelay: "50ms" }}>
          <Stat
            label="Workers"
            value={
              workers.data ? (
                `${workers.data.healthy_workers}/${workers.data.total_workers}`
              ) : (
                <Skeleton className="h-7 w-12" />
              )
            }
            hint={workers.data ? `${formatPercent(utilization)} utilization` : ""}
            icon={<Users size={16} />}
          />
        </div>
        <div className="glass-card p-4 animate-slide-in-up" style={{ animationDelay: "100ms" }}>
          <Stat
            label="Completed"
            value={stats.data ? stats.data.completed_sessions : <Skeleton className="h-7 w-12" />}
            hint={stats.data ? `${stats.data.active_sessions} active · ${stats.data.failed_sessions} failed` : ""}
            icon={<CheckCircle2 size={16} />}
          />
        </div>
        <div className="glass-card p-4 animate-slide-in-up" style={{ animationDelay: "150ms" }}>
          <Stat
            label="Avg risk"
            value={
              stats.data ? (
                stats.data.risk_score_stats.average_risk_score.toFixed(3)
              ) : (
                <Skeleton className="h-7 w-16" />
              )
            }
            hint={stats.data ? `${stats.data.risk_score_stats.high_risk_sessions} high risk` : ""}
            icon={<AlertTriangle size={16} />}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card title="Completed sessions" description={`Last ${MAX_SAMPLES} samples`}>
          <div className="flex items-center justify-between">
            <div className="text-2xl font-semibold text-zinc-50">{stats.data?.completed_sessions ?? "—"}</div>
            <Sparkline data={completedHist} color="#10b981" width={140} height={40} />
          </div>
        </Card>
        <Card title="Failed sessions" description={`Last ${MAX_SAMPLES} samples`}>
          <div className="flex items-center justify-between">
            <div className="text-2xl font-semibold text-zinc-50">{stats.data?.failed_sessions ?? "—"}</div>
            <Sparkline data={failedHist} color="#ef4444" width={140} height={40} />
          </div>
        </Card>
        <Card title="Average risk" description={`Last ${MAX_SAMPLES} samples`}>
          <div className="flex items-center justify-between">
            <div className="text-2xl font-semibold text-zinc-50">
              {stats.data?.risk_score_stats.average_risk_score.toFixed(3) ?? "—"}
            </div>
            <Sparkline data={riskHist} color="#f59e0b" width={140} height={40} />
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Component health" description="Live status of each dependency.">
          {health.error ? (
            <ErrorState error={health.error} onRetry={() => health.mutate()} />
          ) : !health.data ? (
            <Skeleton className="h-32 w-full" />
          ) : (
            <ul className="space-y-2 text-sm">
              {Object.entries(health.data.components).map(([k, v]) => (
                <li
                  key={k}
                  className="flex items-center justify-between rounded-md border border-border bg-bg-card px-3 py-2 hover:border-accent/30 transition-colors"
                >
                  <span className="capitalize text-zinc-300">{k}</span>
                  <StatusBadge status={v?.status || "unknown"} />
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Active sessions" description="In-flight interviews across the cluster.">
          {active.error ? (
            <ErrorState error={active.error} onRetry={() => active.mutate()} />
          ) : !active.data ? (
            <Skeleton className="h-32 w-full" />
          ) : active.data.sessions.length === 0 ? (
            <EmptyState title="No active sessions" description="Start a new interview to see it here." />
          ) : (
            <ul className="space-y-2 text-sm">
              {active.data.sessions.slice(0, 6).map((s) => (
                <li
                  key={s.session_id}
                  className="flex items-center justify-between rounded-md border border-border bg-bg-card px-3 py-2 hover:border-accent/30 transition-colors"
                >
                  <div>
                    <div className="font-mono text-xs text-zinc-300">{s.session_id}</div>
                    <div className="text-xs text-muted">{s.candidate_id}</div>
                  </div>
                  <StatusBadge status={s.status} />
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title="Workers" description="Currently registered worker nodes.">
        {workers.error ? (
          <ErrorState error={workers.error} onRetry={() => workers.mutate()} />
        ) : !workers.data ? (
          <Skeleton className="h-24 w-full" />
        ) : workers.data.workers.length === 0 ? (
          <EmptyState title="No workers registered" description="Workers self-register via the worker_agent on startup." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted">
                <tr>
                  <th className="py-2 pr-4">Worker</th>
                  <th className="py-2 pr-4">Status</th>
                  <th className="py-2 pr-4">Load</th>
                  <th className="py-2 pr-4">Last heartbeat</th>
                </tr>
              </thead>
              <tbody>
                {workers.data.workers.map((w) => (
                  <tr key={w.worker_id} className="border-t border-border hover:bg-white/5 transition-colors">
                    <td className="py-2 pr-4 font-mono text-xs text-zinc-200">{w.worker_id}</td>
                    <td className="py-2 pr-4">
                      <StatusBadge status={w.health_status} />
                    </td>
                    <td className="py-2 pr-4">
                      {w.active_tasks}/{w.capacity}
                    </td>
                    <td className="py-2 pr-4 text-muted">{formatRelative(w.last_heartbeat)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
