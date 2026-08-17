"use client";
import { Dialog, DialogContent, DialogTitle } from "@/components/Dialog";
import { useEffect } from "react";
import { Command, Search, Users, Activity, BarChart3, Settings, LayoutDashboard, Keyboard } from "lucide-react";
import { jsx, jsxs } from "react/jsx-runtime";
const SHORTCUTS = [
  { keys: ["\u2318", "K"], label: "Open command palette", icon: Search },
  { keys: ["G", "S"], label: "Go to Sessions", icon: Activity },
  { keys: ["G", "W"], label: "Go to Workers", icon: Users },
  { keys: ["G", "A"], label: "Go to Analytics", icon: BarChart3 },
  { keys: ["G", "O"], label: "Go to Overview", icon: LayoutDashboard },
  { keys: ["G", ","], label: "Go to Settings", icon: Settings },
  { keys: ["?"], label: "Show this help", icon: Keyboard },
  { keys: ["ESC"], label: "Close dialog", icon: Command }
];
function ShortcutsHelp({ open, onClose }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  return /* @__PURE__ */ jsx(Dialog, { open, onOpenChange: (o) => !o && onClose(), children: /* @__PURE__ */ jsxs(DialogContent, { onClose, className: "max-w-md", children: [
    /* @__PURE__ */ jsxs("div", { className: "border-b border-border px-5 py-4", children: [
      /* @__PURE__ */ jsx(DialogTitle, { children: "Keyboard shortcuts" }),
      /* @__PURE__ */ jsx("p", { className: "mt-0.5 text-xs text-muted", children: "Navigate faster with these shortcuts." })
    ] }),
    /* @__PURE__ */ jsx("div", { className: "p-3", children: SHORTCUTS.map((s) => /* @__PURE__ */ jsxs(
      "div",
      {
        className: "flex items-center justify-between gap-3 rounded-md px-3 py-2 hover:bg-bg-card",
        children: [
          /* @__PURE__ */ jsxs("div", { className: "flex items-center gap-2 text-sm text-zinc-200", children: [
            /* @__PURE__ */ jsx(s.icon, { size: 14, className: "text-muted" }),
            s.label
          ] }),
          /* @__PURE__ */ jsx("div", { className: "flex items-center gap-1", children: s.keys.map((k) => /* @__PURE__ */ jsx(
            "kbd",
            {
              className: "rounded border border-border bg-bg-card px-1.5 py-0.5 text-[10px] font-mono text-zinc-300",
              children: k
            },
            k
          )) })
        ]
      },
      s.label
    )) })
  ] }) });
}
export {
  ShortcutsHelp
};
