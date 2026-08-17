"use client";
import { useState, useMemo } from "react";
import useSWR from "swr";
import { Cpu, Server, Activity } from "lucide-react";
import Card from "@/components/Card";
import Stat from "@/components/Stat";
import { StatusBadge, Badge } from "@/components/Badge";
import { Skeleton, ErrorState, EmptyState } from "@/components/States";
import { SearchInput } from "@/components/ui";
import { Table, Thead, Tbody, Tr, Th, Td } from "@/components/ui";
import { formatPercent, formatRelative } from "@/lib/utils";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function WorkersPage() {
  const workers = useSWR("/workers", { refreshInterval: 4000 });
  const stats = useSWR("/worker-statistics", { refreshInterval: 5000 });
  const scheduling = useSWR("/scheduling-status", { refreshInterval: 5000 });
  const [search, setSearch] = useState("");
  const [sortConfig, setSortConfig] = useState({ key: "", order: "asc" });

  const filtered = useMemo(() => {
    if (!workers.data?.workers) return [];
    if (!search.trim()) return workers.data.workers;
    const q = search.toLowerCase();
    return workers.data.workers.filter((w) =>
      w.worker_id.toLowerCase().includes(q)
    );
  }, [workers.data?.workers, search]);
  const sorted = useMemo(() => {
    let data = filtered;
    if (search.trim()) {
      const q = search.toLowerCase();
      data = data.filter((w) =>
        w.worker_id.toLowerCase().includes(q)
      );
    }

    if (sortConfig.key && sortConfig.order) {
      data = [...data].sort((a, b) => {
        const aVal = a[sortConfig.key];
        const bVal = b[sortConfig.key];

        if (aVal < bVal) return sortConfig.order === "asc" ? -1 : 1;
        if (aVal > bVal) return sortConfig.order === "asc" ? 1 : -1;
        return 0;
      });
    }

    return data;
  }, [workers.data?.workers, search, sortConfig]);
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
          value={
            scheduling.data?.current_strategy ?? (
              <Skeleton className="h-7 w-24" />
            )
          }
          hint={
            scheduling.data?.can_accept_tasks
              ? "Accepting tasks"
              : "At capacity"
          }
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
          <EmptyState
            title="No workers"
            description="Workers register themselves on startup."
          />
        ) : filtered.length === 0 ? (
          <EmptyState title="No matches" description="Try a different filter." />
        ) : (
          <Table>
            <Thead>
              <Tr>
                <Th>Worker</Th>
                <Th>Status</Th>
                <Th>Active</Th>
                <Th>Capacity</Th>
                <Th>Utilization</Th>
                <Th>Heartbeat</Th>
              </Tr>
            </Thead>
            <Tbody>
              {filtered.map((w) => {
                const util = w.capacity
                  ? (w.active_tasks / w.capacity) * 100
                  : 0;
                return (
                  <Tr key={w.worker_id}>
                    <Td className="font-mono text-xs text-zinc-200">
                      {w.worker_id}
                    </Td>
                    <Td>
                      <StatusBadge status={w.health_status} />
                    </Td>
                    <Td>{w.active_tasks}</Td>
                    <Td>{w.capacity}</Td>
                    <Td>
                      <Badge
                        variant={
                          util > 90
                            ? "danger"
                            : util > 70
                            ? "warn"
                            : "success"
                        }
                      >
                        {formatPercent(util)}
                      </Badge>
                    </Td>
                    <Td className="text-muted">
                      {formatRelative(w.last_heartbeat)}
                    </Td>
                  </Tr>
                );
              })}
            </Tbody>
          </Table>
        )}
      </Card>
    </div>
  );
}
