"use client";
import { useState, useMemo, lazy, Suspense, useCallback } from "react";
import useSWR from "swr";
import { Play, RefreshCcw, X } from "lucide-react";
import Card from "@/components/Card";
import { StatusBadge, Badge } from "@/components/Badge";
import { Skeleton, ErrorState, EmptyState } from "@/components/States";
import { SearchInput, Table, Thead, Tbody, Tr, Th, Td, Button, Input } from "@/components/ui";
import Pipeline from "@/components/Pipeline";
import { endpoints } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { cn, formatDate, riskColor } from "@/lib/utils";
import { toast } from "@/lib/toast";
import { useWebSocket } from "@/hooks/useWebSocket";
import { ErrorBoundary } from "@/components/ErrorBoundary";

const SessionDetail = lazy(() => import("@/components/SessionDetail"));

const TABS = ["active", "completed", "failed"];

function SessionComparison({ sessions, onClose }) {
  if (sessions.length < 2) return null;
  const fields = [
    { label: "Status", key: "status" },
    { label: "Risk Score", key: "risk_score", format: (v) => (v != null ? v.toFixed(3) : "—") },
    { label: "Candidate", key: "candidate_id" },
    { label: "Worker", key: "assigned_node", fallback: "—" },
    { label: "Created", key: "created_at", format: (v) => formatDate(v) },
    { label: "Updated", key: "updated_at", format: (v) => formatDate(v) },
    {
      label: "Duration",
      key: null,
      compute: (s) => {
        if (!s.start_time || !s.end_time) return "—";
        const ms = new Date(s.end_time) - new Date(s.start_time);
        const sec = Math.round(ms / 1000);
        if (sec < 60) return `${sec}s`;
        return `${Math.round(sec / 60)}m ${sec % 60}s`;
      },
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="w-full max-w-3xl rounded-xl border border-border bg-bg-panel shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h3 className="text-sm font-semibold text-zinc-100">
            Compare Sessions ({sessions.length})
          </h3>
          <Button
            variant="secondary"
            size="sm"
            onClick={onClose}
            icon={<X size={14} />}
            aria-label="Close comparison"
          />
        </div>
        <div className="overflow-x-auto p-5">
          <Table>
            <Thead>
              <Tr>
                <Th>Field</Th>
                {sessions.map((s) => (
                  <Th key={s.session_id} className="font-mono text-zinc-300 normal-case tracking-normal">
                    {s.session_id.slice(0, 12)}&hellip;
                  </Th>
                ))}
              </Tr>
            </Thead>
            <Tbody>
              {fields.map((f) => (
                <Tr key={f.label}>
                  <Td className="text-xs text-muted">{f.label}</Td>
                  {sessions.map((s) => {
                    const raw = f.compute ? f.compute(s) : s[f.key];
                    const value = f.format ? f.format(raw) : (raw ?? f.fallback ?? "—");
                    return (
                      <Td key={s.session_id} className="text-zinc-300">
                        {f.key === "status" ? <StatusBadge status={raw} /> : value}
                      </Td>
                    );
                  })}
                </Tr>
              ))}
            </Tbody>
          </Table>
        </div>
      </div>
    </div>
  );
}

export default function SessionsPage() {
  const [tab, setTab] = useState("active");
  const [search, setSearch] = useState("");
  const [openId, setOpenId] = useState(null);
  const [compareIds, setCompareIds] = useState([]);
  const token = useAppStore((s) => s.token);

  const active = useSWR("/active-sessions", { refreshInterval: 2000 });
  const completed = useSWR("/completed-sessions?limit=100", { refreshInterval: 10000 });
  const failed = useSWR("/failed-sessions?limit=100", { refreshInterval: 10000 });

  const data = tab === "active" ? active : tab === "completed" ? completed : failed;

  const { connected } = useWebSocket({
    path: "/monitoring/ws/metrics",
    enabled: !!token,
    onMessage: useCallback(() => {
      active.mutate();
      completed.mutate();
      failed.mutate();
    }, [active, completed, failed]),
  });

  const filtered = useMemo(() => {
    if (!data.data?.sessions) return [];
    if (!search.trim()) return data.data.sessions;
    const q = search.toLowerCase();
    return data.data.sessions.filter(
      (s) =>
        s.session_id.toLowerCase().includes(q) ||
        (s.candidate_id || "").toLowerCase().includes(q)
    );
  }, [data.data?.sessions, search]);

  const toggleCompare = useCallback((id) => {
    setCompareIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id].slice(-4)
    );
  }, []);

  const compareSessions = useMemo(
    () =>
      [...(completed.data?.sessions ?? []), ...(failed.data?.sessions ?? [])].filter(
        (s) => compareIds.includes(s.session_id)
      ),
    [completed.data, failed.data, compareIds]
  );

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">Sessions</h1>
          <p className="text-sm text-muted">
            Start new interviews and review historical results.
          </p>
        </div>

        <StartInterviewForm disabled={!token} />
        </div>

        <Card>
        <div className="mb-4 flex flex-wrap items-center gap-2">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                "rounded-md px-3 py-1.5 text-xs font-medium capitalize transition-colors",
                tab === t
                  ? "bg-accent/15 text-accent-light"
                  : "text-muted hover:bg-bg-card hover:text-zinc-200"
              )}
            >
              {t}
            </button>
          ))}
          <div className="ml-auto flex items-center gap-2">
            <SearchInput
              value={search}
              onChange={setSearch}
              placeholder="Filter by id or candidate..."
              className="w-64"
            />
            <Button
              variant="secondary"
              size="sm"
              onClick={() => data.mutate()}
              icon={<RefreshCcw size={12} />}
            >
              Refresh
            </Button>
          </div>
        </div>

        {data.error ? (
          <ErrorState error={data.error} onRetry={() => data.mutate()} />
        ) : !data.data ? (
          <Skeleton className="h-32 w-full" />
        ) : filtered.length === 0 ? (
          <EmptyState
            title={search ? "No matches" : `No ${tab} sessions`}
            description={
              search
                ? "Try a different search term."
                : "Sessions matching this state will appear here."
            }
          />
        ) : (
          <Table>
            <Thead>
              <Tr>
                {tab !== "active" && <Th className="w-8" />}
                <Th>Session</Th>
                <Th>Pipeline</Th>
                <Th>Status</Th>
                <Th>Risk</Th>
                <Th>Worker</Th>
                <Th>Updated</Th>
              </Tr>
            </Thead>
            <Tbody>
              {filtered.map((s) => (
                <Tr key={s.session_id}>
                  {tab !== "active" && (
                    <Td>
                      <input
                        type="checkbox"
                        checked={compareIds.includes(s.session_id)}
                        onChange={() => toggleCompare(s.session_id)}
                        className="rounded border-border"
                      />
                    </Td>
                  )}
                  <Td
                    onClick={() => setOpenId(s.session_id)}
                    className="cursor-pointer font-mono text-xs text-zinc-300 hover:text-accent-light transition-colors"
                  >
                    {s.session_id}
                  </Td>
                  <Td>
                    <Pipeline current={s.status} />
                  </Td>
                  <Td>
                    <StatusBadge status={s.status} />
                  </Td>
                  <Td>
                    {s.risk_score != null ? (
                      <Badge variant={riskColor(s.risk_score)}>
                        {s.risk_score.toFixed(2)}
                      </Badge>
                    ) : (
                      <span className="text-muted">—</span>
                    )}
                  </Td>
                  <Td className="font-mono text-xs text-muted">
                    {s.assigned_node ?? "—"}
                  </Td>
                  <Td className="text-muted">
                    {formatDate(s.updated_at ?? s.end_time)}
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </Card>

      <Suspense fallback={null}>
        <SessionDetail sessionId={openId} onClose={() => setOpenId(null)} />
      </Suspense>

      {compareIds.length >= 2 && (
        <SessionComparison
          sessions={compareSessions}
          onClose={() => setCompareIds([])}
        />
      )}
    </div>
  );
}

function StartInterviewForm({ disabled }) {
  const [candidate, setCandidate] = useState("");
  const [priority, setPriority] = useState("medium");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function submit(e) {
    e.preventDefault();
    if (!candidate.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const r = await endpoints.startInterview({
        candidate_id: candidate.trim(),
        priority,
      });
      toast.success("Interview started", `Session ${r.session_id} queued for processing`);
      setCandidate("");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      toast.error("Failed to start interview", msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card title="Start interview" description="Enqueue a new session for processing.">
      <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
        <Input
          label="Candidate ID"
          value={candidate}
          onChange={(e) => setCandidate(e.target.value)}
          placeholder="cand-1234"
          className="min-w-[200px] flex-1"
        />
        <div>
          <label className="block text-xs text-muted">Priority</label>
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="mt-1 rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-100 focus:border-accent focus:outline-none"
          >
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
          </select>
        </div>
        <Button
          type="submit"
          variant="primary"
          size="lg"
          loading={submitting}
          disabled={disabled || !candidate.trim()}
          icon={<Play size={14} />}
        >
          {submitting ? "Starting…" : "Start"}
        </Button>
      </form>
      {error && <div className="mt-3 text-xs text-rose-400">{error}</div>}
      {disabled && (
        <div className="mt-2 text-xs text-amber-400">
          Set an API token in the top bar to start sessions.
        </div>
      )}
    </Card>
  );
}
