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
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

/**
 * Topbar — the main navigation header of the dashboard.
 * Contains the command-palette trigger, live status, theme toggle,
 * keyboard shortcuts, screen lock, and API token management.
 */
function Topbar() {
  const { token, setToken } = useAppStore();
  const theme = useThemeStore((s) => s.theme);
  const cycleTheme = useThemeStore((s) => s.cycle);
  const setMobile = useUIStore((s) => s.setMobileSidebar);
  const [draft, setDraft] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);

  useEffect(() => { setDraft(token || ""); }, [token]);

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
    theme === "dark" ? "Dark" : theme === "light" ? "Light" : "System";

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-bg-panel px-4 md:px-5">
      {/* Left: mobile menu + command palette trigger */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setMobile(true)}
          icon={<Menu size={18} />}
          aria-label="Open menu"
          className="md:hidden"
        />

        <button
          id="topbar-command-palette"
          onClick={() =>
            window.dispatchEvent(new CustomEvent("open-command-palette"))
          }
          className="flex items-center gap-2 rounded-md border border-border bg-bg-card px-3 py-1.5 text-xs text-muted hover:border-accent/40 hover:text-zinc-200 transition-colors"
        >
          <Search size={14} />
          <span className="hidden sm:inline">Search&hellip;</span>
          <kbd className="hidden rounded border border-border bg-bg-panel px-1 text-[10px] sm:inline">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Right: status indicators + auth */}
      <div className="flex items-center gap-1.5">
        {/* Live WS indicator */}
        <Tooltip content={connected ? "Live updates connected" : "Live updates disconnected"}>
          <div className="flex items-center gap-1.5 rounded-md border border-border bg-bg-card px-2.5 py-1.5 text-[10px] text-muted">
            <Radio
              size={11}
              className={connected ? "text-emerald-400" : "text-muted"}
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

        {/* Theme toggle */}
        <Tooltip content={`Theme: ${themeLabel} (click to cycle)`}>
          <Button
            variant="secondary"
            size="sm"
            onClick={cycleTheme}
            icon={<ThemeIcon size={14} />}
            aria-label="Toggle theme"
          />
        </Tooltip>

        {/* Keyboard shortcuts */}
        <Tooltip content="Keyboard shortcuts (?)">
          <Button
            variant="secondary"
            size="sm"
            onClick={() =>
              window.dispatchEvent(new CustomEvent("open-shortcuts-help"))
            }
            icon={<Keyboard size={14} />}
            aria-label="Show shortcuts"
          />
        </Tooltip>

        {/* Screen lock */}
        <Tooltip content="Lock screen">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              localStorage.setItem("intelliview_screen_lock", "locked");
              window.location.reload();
            }}
            icon={<Lock size={14} />}
            aria-label="Lock screen"
          />
        </Tooltip>

        {/* API token management */}
        {showForm ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setToken(draft.trim() || null);
              setShowForm(false);
            }}
            className="flex items-center gap-2"
          >
            <Input
              type="password"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="API token"
              inputClassName="py-1.5 text-xs"
            />
            <Button type="submit" variant="primary" size="sm">
              Save
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setShowForm(false)}
            >
              Cancel
            </Button>
          </form>
        ) : token ? (
          <Button
            variant="danger"
            size="sm"
            onClick={() => setToken(null)}
            icon={<LogOut size={14} />}
          >
            <span className="hidden sm:inline">Sign out</span>
          </Button>
        ) : (
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowForm(true)}
            icon={<LogIn size={14} />}
          >
            <span className="hidden sm:inline">Set API token</span>
          </Button>
        )}
      </div>
    </header>
  );
}

export { Topbar };
