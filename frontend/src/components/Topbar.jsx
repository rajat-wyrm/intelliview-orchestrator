"use client";
import { useAppStore } from "@/lib/store";
import { useThemeStore } from "@/lib/theme";
import { useEffect, useState } from "react";
import { LogIn, LogOut, Menu, Moon, Sun, Monitor, Search, Keyboard, Radio, Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/lib/ui-store";
import { Tooltip } from "@/components/Tooltip";
import { useWebSocket } from "@/hooks/useWebSocket";
import { jsx, jsxs } from "react/jsx-runtime";
function Topbar() {
  const { token, setToken } = useAppStore();
  const theme = useThemeStore((s) => s.theme);
  const cycleTheme = useThemeStore((s) => s.cycle);
  const setMobile = useUIStore((s) => s.setMobileSidebar);
  const [draft, setDraft] = useState("");
  const [showForm, setShowForm] = useState(false);
  useEffect(() => {
    setDraft(token || "");
  }, [token]);
  const { connected } = useWebSocket({ path: "/monitoring/ws/metrics", enabled: !!token });
  const ThemeIcon = theme === "dark" ? Moon : theme === "light" ? Sun : Monitor;
  const themeLabel = theme === "dark" ? "Dark" : theme === "light" ? "Light" : "System";
  return /* @__PURE__ */ jsxs("header", { className: "flex h-14 items-center justify-between border-b border-border bg-bg-panel px-4 md:px-5", children: [
    /* @__PURE__ */ jsxs("div", { className: "flex items-center gap-3", children: [
      /* @__PURE__ */ jsx(
        "button",
        {
          onClick: () => setMobile(true),
          className: "rounded-md p-1.5 text-zinc-400 hover:bg-bg-card hover:text-zinc-100 md:hidden",
          "aria-label": "Open menu",
          children: /* @__PURE__ */ jsx(Menu, { size: 18 })
        }
      ),
      /* @__PURE__ */ jsxs(
        "button",
        {
          onClick: () => window.dispatchEvent(new CustomEvent("open-command-palette")),
          className: "flex items-center gap-2 rounded-md border border-border bg-bg-card px-3 py-1.5 text-xs text-muted hover:border-accent/40 hover:text-zinc-200",
          children: [
            /* @__PURE__ */ jsx(Search, { size: 14 }),
            /* @__PURE__ */ jsx("span", { className: "hidden sm:inline", children: "Search\u2026" }),
            /* @__PURE__ */ jsx("kbd", { className: "hidden rounded border border-border bg-bg-panel px-1 text-[10px] sm:inline", children: "\u2318K" })
          ]
        }
      )
    ] }),
    /* @__PURE__ */ jsxs("div", { className: "flex items-center gap-1.5", children: [
      /* @__PURE__ */ jsx(Tooltip, { content: connected ? "Live updates connected" : "Live updates disconnected", children: /* @__PURE__ */ jsxs("div", { className: "flex items-center gap-1.5 rounded-md border border-border bg-bg-card px-2.5 py-1.5 text-[10px] text-muted", children: [
        /* @__PURE__ */ jsx(Radio, { size: 11, className: connected ? "text-emerald-400" : "text-muted" }),
        /* @__PURE__ */ jsx("span", { className: cn("hidden sm:inline", connected && "text-emerald-400"), children: connected ? "Live" : "Offline" })
      ] }) }),
      /* @__PURE__ */ jsx(Tooltip, { content: `Theme: ${themeLabel} (click to cycle)`, children: /* @__PURE__ */ jsx(
        "button",
        {
          onClick: cycleTheme,
          className: "rounded-md border border-border bg-bg-card p-1.5 text-muted hover:text-zinc-200",
          "aria-label": "Toggle theme",
          children: /* @__PURE__ */ jsx(ThemeIcon, { size: 14 })
        }
      ) }),
      /* @__PURE__ */ jsx(Tooltip, { content: "Keyboard shortcuts (?)", children: /* @__PURE__ */ jsx(
        "button",
        {
          onClick: () => window.dispatchEvent(new CustomEvent("open-shortcuts-help")),
          className: "rounded-md border border-border bg-bg-card p-1.5 text-muted hover:text-zinc-200",
          "aria-label": "Show shortcuts",
          children: /* @__PURE__ */ jsx(Keyboard, { size: 14 })
        }
      ) }),
      /* @__PURE__ */ jsx(Tooltip, { content: "Lock screen", children: /* @__PURE__ */ jsx(
        "button",
        {
          onClick: () => {
            localStorage.setItem("intelliview_screen_lock", "locked");
            window.location.reload();
          },
          className: "rounded-md border border-border bg-bg-card p-1.5 text-muted hover:text-zinc-200",
          "aria-label": "Lock screen",
          children: /* @__PURE__ */ jsx(Lock, { size: 14 })
        }
      ) }),
      showForm ? /* @__PURE__ */ jsxs(
        "form",
        {
          onSubmit: (e) => {
            e.preventDefault();
            setToken(draft.trim() || null);
            setShowForm(false);
          },
          className: "flex items-center gap-2",
          children: [
            /* @__PURE__ */ jsx(
              "input",
              {
                type: "password",
                value: draft,
                onChange: (e) => setDraft(e.target.value),
                placeholder: "API token",
                className: "rounded-md border border-border bg-bg-card px-3 py-1.5 text-xs text-zinc-100 placeholder:text-muted focus:border-accent focus:outline-none"
              }
            ),
            /* @__PURE__ */ jsx("button", { type: "submit", className: "rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-dark", children: "Save" }),
            /* @__PURE__ */ jsx("button", { type: "button", onClick: () => setShowForm(false), className: "rounded-md border border-border bg-bg-card px-3 py-1.5 text-xs text-zinc-300 hover:bg-bg-panel", children: "Cancel" })
          ]
        }
      ) : token ? /* @__PURE__ */ jsxs(
        "button",
        {
          onClick: () => setToken(null),
          className: cn(
            "flex items-center gap-1.5 rounded-md border border-border bg-bg-card px-3 py-1.5 text-xs text-zinc-300",
            "hover:border-rose-500/40 hover:text-rose-300"
          ),
          children: [
            /* @__PURE__ */ jsx(LogOut, { size: 14 }),
            /* @__PURE__ */ jsx("span", { className: "hidden sm:inline", children: "Sign out" })
          ]
        }
      ) : /* @__PURE__ */ jsxs(
        "button",
        {
          onClick: () => setShowForm(true),
          className: "flex items-center gap-1.5 rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-dark",
          children: [
            /* @__PURE__ */ jsx(LogIn, { size: 14 }),
            /* @__PURE__ */ jsx("span", { className: "hidden sm:inline", children: "Set API token" })
          ]
        }
      )
    ] })
  ] });
}
export {
  Topbar
};
