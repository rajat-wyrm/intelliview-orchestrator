"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Users,
  Activity,
  BarChart3,
  Settings,
  Shield,
  Video,
  UserCircle,
} from "lucide-react";

const items = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/interview", label: "Interview", icon: Video },
  { href: "/sessions", label: "Sessions", icon: Activity },
  { href: "/candidates", label: "Candidates", icon: UserCircle },
  { href: "/workers", label: "Workers", icon: Users },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar({ mobile = false, onNavigate }) {
  const pathname = usePathname();

  return (
    <aside
      className={cn(
        mobile
          ? "flex w-full flex-col"
          : "hidden w-60 shrink-0 border-r border-border bg-bg-panel md:flex md:flex-col"
      )}
      aria-label="Sidebar"
    >
      {/* Logo */}
      <div className="flex h-14 items-center gap-2 border-b border-border px-5">
        <div
          className="flex h-8 w-8 items-center justify-center rounded-md bg-accent text-white"
          aria-hidden="true"
        >
          <Shield size={16} />
        </div>

        <div>
          <div className="text-sm font-semibold text-zinc-100">
            AI-Intelliview
          </div>

          <div className="text-[10px] uppercase tracking-wider text-muted">
            Orchestrator
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav
        className="flex-1 space-y-1 p-3"
        aria-label="Primary Navigation"
      >
        {items.map((item) => {
          const active =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));

          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              aria-label={item.label}
              aria-current={active ? "page" : undefined}
              className={cn(
                "group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-200",
                "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-bg-panel",
                active
                  ? "bg-accent/20 text-accent-light"
                  : "text-zinc-300 hover:bg-bg-card hover:text-white"
              )}
            >
              <Icon
                size={18}
                aria-hidden="true"
                className="shrink-0"
              />

              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <footer
        className="border-t border-border p-4 text-[10px] text-muted"
        aria-label="Application Version"
      >
        <span>v0.2.0</span>
        <span className="mx-1">•</span>
        <span>© Mukta Redij</span>
      </footer>
    </aside>
  );
}
