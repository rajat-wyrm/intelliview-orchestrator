"use client";

import { useAppStore } from "@/lib/store";
import { useThemeStore } from "@/lib/theme";
import { useEffect, useState } from "react";
import {
  LogIn,
  LogOut,
  Menu,
  Moon,
  Sun,
  Monitor,
  Search,
  Keyboard,
  Radio,
  Lock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/lib/ui-store";
import { Tooltip } from "@/components/Tooltip";
import { useWebSocket } from "@/hooks/useWebSocket";

function Topbar() {
  const { token, setToken } = useAppStore();
  const theme = useThemeStore((s) => s.theme);
  const cycleTheme = useThemeStore((s) => s.cycle);
  const setMobile = useUIStore((s) => s.setMobileSidebar);

  const [draft, setDraft] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [, setPaletteOpen] = useState(false);
  const [, setHelpOpen] = useState(false);

  useEffect(() => {
    setDraft(token || "");
  }, [token]);

  useEffect(() => {
    const onPalette = () => setPaletteOpen(true);
    const onHelp = () => setHelpOpen(true);

    window.addEventListener("open-command-palette", onPalette);
    window.addEventListener("open-shortcuts-help", onHelp);

    return () => {
      window.removeEventListener("open-command-palette", onPalette);
      window.removeEventListener("open-shortcuts-help", onHelp);
    };
  }, []);

  const { connected } = useWebSocket({
    path: "/monitoring/ws/metrics",
    enabled: !!token,
  });

  const ThemeIcon =
    theme === "dark" ? Moon : theme === "light" ? Sun : Monitor;

  const themeLabel =
    theme === "dark"
      ? "Dark"
      : theme === "light"
      ? "Light"
      : "System";

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-bg-panel px-4 md:px-5">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => setMobile(true)}
          aria-label="Open navigation menu"
          title="Open navigation menu"
          className="rounded-md p-1.5 text-zinc-300 transition-colors hover:bg-bg-card hover:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-bg-panel md:hidden"
        >
          <Menu size={18} aria-hidden="true" />
        </button>

        <button
          type="button"
          onClick={() =>
            window.dispatchEvent(new CustomEvent("open-command-palette"))
          }
          aria-label="Open command palette"
          title="Open command palette (Ctrl+K)"
          className="flex items-center gap-2 rounded-md border border-border bg-bg-card px-3 py-1.5 text-xs text-zinc-300 transition-colors hover:border-accent/40 hover:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-bg-panel"
        >
          <Search size={14} aria-hidden="true" />

          <span className="hidden sm:inline">Search…</span>

          <kbd className="hidden rounded border border-border bg-bg-panel px-1 text-[10px] sm:inline">
            ⌘K
          </kbd>
        </button>
      </div>

      <div className="flex items-center gap-1.5">
        <Tooltip
          content={
            connected
              ? "Live updates connected"
              : "Live updates disconnected"
          }
        >
          <div
            className="flex items-center gap-1.5 rounded-md border border-border bg-bg-card px-2.5 py-1.5 text-[10px] text-muted"
            aria-live="polite"
          >
            <Radio
              size={11}
              aria-hidden="true"
              className={
                connected ? "text-emerald-400" : "text-muted"
              }
            />

            <span
              className={cn(
                "hidden sm:inline",
                connected && "text-emerald-400"
              )}
            >
              {connected ? "Live" : "Offline"}
            </span>
          </div>
        </Tooltip>

        <Tooltip content={`Theme: ${themeLabel} (click to cycle)`}>
          <button
            type="button"
            onClick={cycleTheme}
            aria-label={`Current theme: ${themeLabel}. Click to switch theme`}
            title={`Current theme: ${themeLabel}`}
            className="rounded-md border border-border bg-bg-card p-1.5 text-zinc-300 transition-colors hover:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-bg-panel"
          >
            <ThemeIcon size={14} aria-hidden="true" />
          </button>
        </Tooltip>

        <Tooltip content="Keyboard shortcuts (?)">
          <button
            type="button"
            onClick={() =>
              window.dispatchEvent(new CustomEvent("open-shortcuts-help"))
            }
            aria-label="Show keyboard shortcuts"
            title="Keyboard shortcuts"
            className="rounded-md border border-border bg-bg-card p-1.5 text-zinc-300 transition-colors hover:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-bg-panel"
          >
            <Keyboard size={14} aria-hidden="true" />
          </button>
        </Tooltip>

        <Tooltip content="Lock screen">
          <button
            type="button"
            onClick={() => {
              localStorage.setItem(
                "intelliview_screen_lock",
                "locked"
              );
              window.location.reload();
            }}
            aria-label="Lock application"
            title="Lock application"
            className="rounded-md border border-border bg-bg-card p-1.5 text-zinc-300 transition-colors hover:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-bg-panel"
          >
            <Lock size={14} aria-hidden="true" />
          </button>
        </Tooltip>        {showForm ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setToken(draft.trim() || null);
              setShowForm(false);
            }}
            className="flex items-center gap-2"
          >
            <input
              type="password"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="API token"
              aria-label="API Token"
              autoComplete="off"
              className="rounded-md border border-border bg-bg-card px-3 py-1.5 text-xs text-zinc-100 placeholder:text-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-blue-500"
            />

            <button
              type="submit"
              className="rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-accent-dark focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-bg-panel"
            >
              Save
            </button>

            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-md border border-border bg-bg-card px-3 py-1.5 text-xs text-zinc-300 transition-colors hover:bg-bg-panel hover:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-bg-panel"
            >
              Cancel
            </button>
          </form>
        ) : token ? (
          <button
            type="button"
            onClick={() => setToken(null)}
            aria-label="Sign out"
            className="flex items-center gap-1.5 rounded-md border border-border bg-bg-card px-3 py-1.5 text-xs text-zinc-300 transition-colors hover:border-rose-500/40 hover:text-rose-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-bg-panel"
          >
            <LogOut size={14} aria-hidden="true" />
            <span className="hidden sm:inline">Sign out</span>
          </button>
        ) : (
          <button
            type="button"
            onClick={() => setShowForm(true)}
            aria-label="Set API Token"
            className="flex items-center gap-1.5 rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-accent-dark focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-bg-panel"
          >
            <LogIn size={14} aria-hidden="true" />
            <span className="hidden sm:inline">Set API token</span>
          </button>
        )}
      </div>
    </header>
  );
}

export {
  Topbar,
};