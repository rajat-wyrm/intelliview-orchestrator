"use client";
import { useState } from "react";
import useSWR from "swr";
import Card from "@/components/Card";
import { Skeleton, ErrorState } from "@/components/States";
import { endpoints } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { useThemeStore } from "@/lib/theme";
import { toast } from "@/lib/toast";
import { Moon, Sun, Monitor, Shield, Trash2, RefreshCw } from "lucide-react";

const THEME_OPTIONS = [
  { v: "dark", label: "Dark", icon: Moon },
  { v: "light", label: "Light", icon: Sun },
  { v: "system", label: "System", icon: Monitor },
];

const STRATEGIES = ["ROUND_ROBIN", "LEAST_LOADED", "QUEUE_BASED"];

export default function SettingsPage() {
  const token = useAppStore((s) => s.token);
  const setToken = useAppStore((s) => s.setToken);
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);

  const [draft, setDraft] = useState("");
  const [switching, setSwitching] = useState(null);
  const [detecting, setDetecting] = useState(false);
  const [clearingCache, setClearingCache] = useState(false);
  const scheduling = useSWR("/scheduling-status", { refreshInterval: 5000 });

  function handleSaveToken(e) {
    e.preventDefault();
    setToken(draft.trim() || null);
    toast.success("API token updated");
  }

  function handleClearToken() {
    setToken(null);
    setDraft("");
    toast.info("Signed out");
  }

  async function handleSwitch(s) {
    setSwitching(s);
    try {
      await endpoints.switchStrategy(s);
      await scheduling.mutate();
      toast.success("Strategy switched", s);
    } catch (err) {
      toast.error("Failed to switch", err instanceof Error ? err.message : String(err));
    } finally {
      setSwitching(null);
    }
  }

  async function handleDetect() {
    setDetecting(true);
    try {
      const r = await endpoints.detectFailures();
      toast.success(
        "Detection complete",
        `${r.failed_sessions_detected} failed · ${r.unhealthy_workers_detected} unhealthy · ${r.stuck_sessions_detected} stuck`,
      );
    } catch (err) {
      toast.error("Detection failed", err instanceof Error ? err.message : String(err));
    } finally {
      setDetecting(false);
    }
  }

  async function handleClearCache() {
    setClearingCache(true);
    try {
      await endpoints.clearCache();
      toast.success("Cache cleared");
    } catch (err) {
      toast.error("Failed to clear cache", err instanceof Error ? err.message : String(err));
    } finally {
      setClearingCache(false);
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">Settings</h1>
          <p className="text-sm text-muted">API credentials, theme, and runtime controls.</p>
        </div>
        <div className="flex items-center gap-2">
          <Shield size={14} className="text-muted" />
          <span className="text-xs text-muted">Secure</span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <Card title="API token" description="Required for worker management and protected endpoints.">
            <form onSubmit={handleSaveToken} className="flex items-center gap-2">
              <input
                type="password"
                value={draft || token || ""}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="paste API_TOKEN"
                className="flex-1 rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-100 placeholder:text-muted focus:border-accent focus:outline-none"
              />
              <button
                type="submit"
                className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-dark"
              >
                Save
              </button>
              {token && (
                <button
                  type="button"
                  onClick={handleClearToken}
                  className="rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-300 hover:bg-bg-panel"
                >
                  Clear
                </button>
              )}
            </form>
          </Card>

          <Card title="Appearance" description="Choose how the dashboard looks.">
            <div className="flex flex-wrap items-center gap-2">
              {THEME_OPTIONS.map((opt) => {
                const Icon = opt.icon;
                const active = theme === opt.v;
                return (
                  <button
                    key={opt.v}
                    onClick={() => {
                      setTheme(opt.v);
                      toast.info(`Theme: ${opt.label}`);
                    }}
                    className={
                      "flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs font-medium transition-all " +
                      (active
                        ? "border-accent bg-accent/15 text-accent-light"
                        : "border-border bg-bg-card text-zinc-300 hover:border-accent/40")
                    }
                  >
                    <Icon size={14} />
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card title="Load balancing" description="Switch the active strategy at runtime.">
            {scheduling.error ? (
              <ErrorState error={scheduling.error} onRetry={() => scheduling.mutate()} />
            ) : !scheduling.data ? (
              <Skeleton className="h-20 w-full" />
            ) : (
              <div className="flex flex-wrap items-center gap-2">
                {STRATEGIES.map((s) => {
                  const active = scheduling.data.current_strategy === s;
                  return (
                    <button
                      key={s}
                      disabled={switching !== null}
                      onClick={() => handleSwitch(s)}
                      className={
                        "rounded-md border px-3 py-1.5 text-xs font-medium transition-all " +
                        (active
                          ? "border-accent bg-accent/15 text-accent-light"
                          : "border-border bg-bg-card text-zinc-300 hover:border-accent/40")
                      }
                    >
                      {s} {switching === s ? "..." : ""}
                    </button>
                  );
                })}
              </div>
            )}
          </Card>

          <Card title="System maintenance" description="Run diagnostics and clear caches.">
            <div className="flex flex-wrap items-center gap-3">
              <button
                disabled={detecting}
                onClick={handleDetect}
                className="flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-dark disabled:opacity-50"
              >
                <RefreshCw size={14} className={detecting ? "animate-spin" : ""} />
                {detecting ? "Scanning..." : "Run detection"}
              </button>
              <button
                disabled={clearingCache}
                onClick={handleClearCache}
                className="flex items-center gap-2 rounded-md border border-border bg-bg-card px-4 py-2 text-sm text-zinc-300 hover:border-rose-500/40 hover:text-rose-300 disabled:opacity-50"
              >
                <Trash2 size={14} />
                {clearingCache ? "Clearing..." : "Clear cache"}
              </button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
