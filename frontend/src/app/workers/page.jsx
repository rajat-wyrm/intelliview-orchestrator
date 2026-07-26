"use client";
import { useState, useMemo } from "react";
import useSWR from "swr";
import { Cpu, Server, Activity } from "lucide-react";
import Card from "@/components/Card";
import Stat from "@/components/Stat";
import { StatusBadge, Badge } from "@/components/Badge";
import { Skeleton, ErrorState, EmptyState } from "@/components/States";
import { SearchInput } from "@/components/SearchInput";
import { formatPercent, formatRelative } from "@/lib/utils";

export default function WorkersPage() {
  const workers = useSWR("/workers", { refreshInterval: 4000 });
  const stats = useSWR("/worker-statistics", { refreshInterval: 5000 });
  const scheduling = useSWR("/scheduling-status", { refreshInterval: 5000 });
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!workers.data?.workers) return [];
    if (!search.trim()) return workers.data.workers;
    const q = search.toLowerCase();
    return workers.data.workers.filter((w) => w.worker_id.toLowerCase().includes(q));
  }, [workers.data?.workers, search]);

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-50">Workers</h1>
        <p className="text-sm text-muted">Registered worker nodes, capacity, and live utilization.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="Total"
          value={stats.data?.total_workers ?? <Skeleton className="h-7 w-12" />}
          icon={<Server size={16} />}
        />
        <Stat
          label="Healthy"
          value={
            stats.data ? (
              `${stats.data.healthy_workers}/${stats.data.total_workers}`
            ) : (
              <Skeleton className="h-7 w-16" />
            )
          }
          icon={<Activity size={16} />}
        />
        <Stat
          label="Utilization"
          value={
            stats.data ? (
              formatPercent(stats.data.system_utilization_percent)
            ) : (
              <Skeleton className="h-7 w-16" />
            )
          }
          icon={<Cpu size={16} />}
        />
        <Stat
          label="Strategy"
          value={scheduling.data?.current_strategy ?? <Skeleton className="h-7 w-24" />}
          hint={scheduling.data?.can_accept_tasks ? "Accepting tasks" : "At capacity"}
        />
      </div>

      <Card
        title="Worker details"
        description="Live per-worker stats."
        action={
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Filter workers…"
            className="w-56"
          />
        }
      >
        {workers.error ? (
          <ErrorState error={workers.error} onRetry={() => workers.mutate()} />
        ) : !workers.data ? (
          <Skeleton className="h-32 w-full" />
        ) : workers.data.workers.length === 0 ? (
          <EmptyState title="No workers" description="Workers register themselves on startup." />
        ) : filtered.length === 0 ? (
          <EmptyState title="No matches" description="Try a different filter." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted">
                <tr>
                  <th className="py-2 pr-4">Worker</th>
                  <th className="py-2 pr-4">Status</th>
                  <th className="py-2 pr-4">Active</th>
                  <th className="py-2 pr-4">Capacity</th>
                  <th className="py-2 pr-4">Utilization</th>
                  <th className="py-2 pr-4">Heartbeat</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((w) => {
                  const util = w.capacity ? (w.active_tasks / w.capacity) * 100 : 0;
                  return (
                    <tr key={w.worker_id} className="border-t border-border">
                      <td className="py-2 pr-4 font-mono text-xs text-zinc-200">{w.worker_id}</td>
                      <td className="py-2 pr-4">
                        <StatusBadge status={w.health_status} />
                      </td>
                      <td className="py-2 pr-4">{w.active_tasks}</td>
                      <td className="py-2 pr-4">{w.capacity}</td>
                      <td className="py-2 pr-4">
                        <Badge variant={util > 90 ? "danger" : util > 70 ? "warn" : "success"}>
                          {formatPercent(util)}
                        </Badge>
                      </td>
                      <td className="py-2 pr-4 text-muted">{formatRelative(w.last_heartbeat)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
