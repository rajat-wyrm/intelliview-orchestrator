"use client";
import { Command } from "cmdk";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Activity,
  Users,
  BarChart3,
  Settings,
  Search,
  Play,
  RefreshCcw,
  Trash2,
  Zap,
  Video,
  UserCircle,
} from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "@/components/Dialog";

const NAV_ITEMS = [
  { id: "nav:overview", label: "Overview", icon: LayoutDashboard, action: "/", group: "Navigate" },
  { id: "nav:interview", label: "Interview", icon: Video, action: "/interview", group: "Navigate" },
  { id: "nav:sessions", label: "Sessions", icon: Activity, action: "/sessions", group: "Navigate" },
  { id: "nav:candidates", label: "Candidates", icon: UserCircle, action: "/candidates", group: "Navigate" },
  { id: "nav:workers", label: "Workers", icon: Users, action: "/workers", group: "Navigate" },
  { id: "nav:analytics", label: "Analytics", icon: BarChart3, action: "/analytics", group: "Navigate" },
  { id: "nav:settings", label: "Settings", icon: Settings, action: "/settings", group: "Navigate" },
];

const ACTIONS = [
  { id: "act:start", label: "Start new interview", icon: Play, action: "start", group: "Actions" },
  { id: "act:live-interview", label: "Start live interview", icon: Video, action: "live-interview", group: "Actions" },
  { id: "act:refresh", label: "Refresh all data", icon: RefreshCcw, action: "refresh", group: "Actions" },
  { id: "act:detect", label: "Run failure detection", icon: Zap, action: "detect", group: "Actions" },
  { id: "act:clear-cache", label: "Clear session cache", icon: Trash2, action: "clear-cache", group: "Actions" },
];

export function CommandPalette({ open, onOpenChange, onAction }) {
  const router = useRouter();
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!open) setSearch("");
  }, [open]);

  function handleSelect(id) {
    const nav = NAV_ITEMS.find((n) => n.id === id);
    if (nav) {
      router.push(nav.action);
      onOpenChange(false);
      return;
    }
    const act = ACTIONS.find((a) => a.id === id);
    if (act) {
      onAction?.(act.action);
      onOpenChange(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl overflow-hidden p-0">
        <DialogTitle className="sr-only">Command palette</DialogTitle>
        <Command label="Command palette" className="bg-bg-panel">
          <div className="flex items-center gap-2 border-b border-border px-4 py-3">
            <Search size={16} className="text-muted" />
            <Command.Input
              value={search}
              onValueChange={setSearch}
              placeholder="Type a command or search…"
              className="flex-1 bg-transparent text-sm text-zinc-100 placeholder:text-muted focus:outline-none"
            />
            <kbd className="rounded border border-border bg-bg-card px-1.5 py-0.5 text-[10px] text-muted">
              ESC
            </kbd>
          </div>

          <Command.List className="max-h-80 overflow-y-auto p-2">
            <Command.Empty className="px-3 py-6 text-center text-sm text-muted">
              No results found.
            </Command.Empty>

            <Command.Group
              heading="Navigate"
              className="text-xs uppercase tracking-wide text-muted"
            >
              {NAV_ITEMS.map((item) => (
                <Command.Item
                  key={item.id}
                  value={item.label}
                  onSelect={() => handleSelect(item.id)}
                  className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-sm text-zinc-200 aria-selected:bg-accent/15 aria-selected:text-accent-light"
                >
                  <item.icon size={16} />
                  <span>{item.label}</span>
                </Command.Item>
              ))}
            </Command.Group>

            <Command.Separator className="my-2 h-px bg-border" />

            <Command.Group
              heading="Actions"
              className="text-xs uppercase tracking-wide text-muted"
            >
              {ACTIONS.map((item) => (
                <Command.Item
                  key={item.id}
                  value={item.label}
                  onSelect={() => handleSelect(item.id)}
                  className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-sm text-zinc-200 aria-selected:bg-accent/15 aria-selected:text-accent-light"
                >
                  <item.icon size={16} />
                  <span>{item.label}</span>
                </Command.Item>
              ))}
            </Command.Group>
          </Command.List>

          <div className="flex items-center justify-between border-t border-border bg-bg-card/50 px-4 py-2 text-[10px] text-muted">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <kbd className="rounded border border-border bg-bg-card px-1">↑↓</kbd>
                navigate
              </span>
              <span className="flex items-center gap-1">
                <kbd className="rounded border border-border bg-bg-card px-1">↵</kbd>
                select
              </span>
            </div>
            <span>Powered by cmdk</span>
          </div>
        </Command>
      </DialogContent>
    </Dialog>
  );
}

export default CommandPalette;
