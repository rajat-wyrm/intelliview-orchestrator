"use client";

import { useEffect, useState } from "react";
import {
LogIn,
LogOut,
Menu,
Moon,
Sun,
Search,
Keyboard,
Radio,
Lock,
} from "lucide-react";

import { useAppStore } from "@/lib/store";
import { useThemeStore } from "@/lib/theme";
import { useUIStore } from "@/lib/ui-store";
import { cn } from "@/lib/utils";
import { Tooltip } from "@/components/Tooltip";
import { useWebSocket } from "@/hooks/useWebSocket";

export function Topbar() {
const { token, setToken } = useAppStore();

const theme = useThemeStore((state) => state.theme);
const toggleTheme = useThemeStore(
(state) => state.toggleTheme
);

const setMobile = useUIStore(
(state) => state.setMobileSidebar
);

const [draft, setDraft] = useState("");
const [showForm, setShowForm] = useState(false);

useEffect(() => {
setDraft(token || "");
}, [token]);

const { connected } = useWebSocket({
path: "/monitoring/ws/metrics",
enabled: !!token,
});

const isDark = theme === "dark";

/*

* Show the icon for the theme the user can switch to.
*
* Dark mode  -> Sun icon (switch to light)
* Light mode -> Moon icon (switch to dark)
  */
  const ThemeIcon = isDark ? Sun : Moon;

const nextThemeLabel = isDark
? "Switch to light mode"
: "Switch to dark mode";

return ( <header className="flex h-14 items-center justify-between border-b border-border bg-bg-panel px-4 md:px-5">
{/* Left section */} <div className="flex items-center gap-3">
{/* Mobile menu */}
<button
type="button"
onClick={() => setMobile(true)}
className="rounded-md p-1.5 text-muted hover:bg-bg-card hover:text-zinc-100"
aria-label="Open navigation menu"
> <Menu size={18} className="md:hidden" /> </button>


    {/* Command palette */}
    <button
      type="button"
      onClick={() =>
        window.dispatchEvent(
          new CustomEvent("open-command-palette")
        )
      }
      className="flex items-center gap-2 rounded-md border border-border bg-bg-card px-3 py-1.5 text-xs text-muted hover:border-accent/40 hover:text-zinc-200"
      aria-label="Open search"
    >
      <Search size={14} />

      <span className="hidden sm:inline">
        Search…
      </span>

      <kbd className="hidden rounded border border-border bg-bg-panel px-1 text-[10px] sm:inline">
        ⌘K
      </kbd>
    </button>
  </div>

  {/* Right section */}
  <div className="flex items-center gap-1.5">
    {/* WebSocket status */}
    <Tooltip
      content={
        connected
          ? "Live updates connected"
          : "Live updates disconnected"
      }
    >
      <div className="flex items-center gap-1.5 rounded-md border border-border bg-bg-card px-2.5 py-1.5 text-[10px] text-muted">
        <Radio
          size={11}
          className={
            connected
              ? "text-emerald-500 dark:text-emerald-400"
              : "text-muted"
          }
        />

        <span
          className={cn(
            "hidden sm:inline",
            connected &&
              "text-emerald-600 dark:text-emerald-400"
          )}
        >
          {connected ? "Live" : "Offline"}
        </span>
      </div>
    </Tooltip>

    {/* Theme toggle */}
    <Tooltip content={nextThemeLabel}>
      <button
        type="button"
        onClick={toggleTheme}
        className="rounded-md border border-border bg-bg-card p-1.5 text-muted hover:border-accent/40 hover:bg-bg-panel hover:text-zinc-200"
        aria-label={nextThemeLabel}
        aria-pressed={isDark}
        title={nextThemeLabel}
      >
        <ThemeIcon size={14} />
      </button>
    </Tooltip>

    {/* Keyboard shortcuts */}
    <Tooltip content="Keyboard shortcuts (?)">
      <button
        type="button"
        onClick={() =>
          window.dispatchEvent(
            new CustomEvent("open-shortcuts-help")
          )
        }
        className="rounded-md border border-border bg-bg-card p-1.5 text-muted hover:border-accent/40 hover:bg-bg-panel hover:text-zinc-200"
        aria-label="Show keyboard shortcuts"
      >
        <Keyboard size={14} />
      </button>
    </Tooltip>

    {/* Screen lock */}
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
        className="rounded-md border border-border bg-bg-card p-1.5 text-muted hover:border-accent/40 hover:bg-bg-panel hover:text-zinc-200"
        aria-label="Lock screen"
      >
        <Lock size={14} />
      </button>
    </Tooltip>

    {/* API token */}
    {showForm ? (
      <form
        onSubmit={(event) => {
          event.preventDefault();

          setToken(draft.trim() || null);
          setShowForm(false);
        }}
        className="flex items-center gap-2"
      >
        <label
          htmlFor="api-token"
          className="sr-only"
        >
          API token
        </label>

        <input
          id="api-token"
          type="password"
          value={draft}
          onChange={(event) =>
            setDraft(event.target.value)
          }
          placeholder="API token"
          autoComplete="off"
          className="rounded-md border border-border bg-bg-card px-3 py-1.5 text-xs text-zinc-100 placeholder:text-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
        />

        <button
          type="submit"
          className="rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-dark focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
        >
          Save
        </button>

        <button
          type="button"
          onClick={() => setShowForm(false)}
          className="rounded-md border border-border bg-bg-card px-3 py-1.5 text-xs text-zinc-300 hover:bg-bg-panel hover:text-zinc-100"
        >
          Cancel
        </button>
      </form>
    ) : token ? (
      <button
        type="button"
        onClick={() => setToken(null)}
        className={cn(
          "flex items-center gap-1.5 rounded-md border border-border bg-bg-card px-3 py-1.5 text-xs text-zinc-300",
          "hover:border-rose-500/40 hover:text-rose-500 dark:hover:text-rose-300"
        )}
      >
        <LogOut size={14} />

        <span className="hidden sm:inline">
          Sign out
        </span>
      </button>
    ) : (
      <button
        type="button"
        onClick={() => setShowForm(true)}
        className="flex items-center gap-1.5 rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-dark focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
      >
        <LogIn size={14} />

        <span className="hidden sm:inline">
          Set API token
        </span>
      </button>
    )}
  </div>
</header>
);
}
