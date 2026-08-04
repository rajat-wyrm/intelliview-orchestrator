"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
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

import { cn } from "@/lib/utils";

const items = [
{
href: "/",
label: "Overview",
icon: LayoutDashboard,
},
{
href: "/interview",
label: "Interview",
icon: Video,
},
{
href: "/sessions",
label: "Sessions",
icon: Activity,
},
{
href: "/candidates",
label: "Candidates",
icon: UserCircle,
},
{
href: "/workers",
label: "Workers",
icon: Users,
},
{
href: "/analytics",
label: "Analytics",
icon: BarChart3,
},
{
href: "/settings",
label: "Settings",
icon: Settings,
},
];

export function Sidebar({
mobile = false,
onNavigate,
}) {
const pathname = usePathname();

return (
<aside
className={cn(
mobile
? "flex w-full flex-col bg-bg-panel"
: "hidden w-60 shrink-0 border-r border-border bg-bg-panel md:flex md:flex-col"
)}
aria-label="Main navigation"
>
{/* =====================================================
BRAND
===================================================== */}


  <div className="flex h-14 items-center gap-2 border-b border-border px-5">
    <div
      className="flex h-8 w-8 items-center justify-center rounded-md bg-accent text-white"
      aria-hidden="true"
    >
      <Shield size={16} />
    </div>

    <div className="min-w-0">
      <div className="truncate text-sm font-semibold text-zinc-900 dark:text-zinc-100">
        AI-Intelliview
      </div>

      <div className="text-[10px] uppercase tracking-wider text-muted">
        Orchestrator
      </div>
    </div>
  </div>

  {/* =====================================================
      NAVIGATION
      ===================================================== */}

  <nav
    className="flex-1 space-y-0.5 p-3"
    aria-label="Primary navigation"
  >
    {items.map((item) => {
      const Icon = item.icon;

      const active =
        pathname === item.href ||
        (item.href !== "/" &&
          pathname.startsWith(item.href));

      return (
        <Link
          key={item.href}
          href={item.href}
          onClick={onNavigate}
          aria-current={active ? "page" : undefined}
          className={cn(
            "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/70",
            active
              ? "bg-accent/15 text-indigo-700 dark:text-accent-light"
              : "text-zinc-600 hover:bg-bg-card hover:text-zinc-950 dark:text-zinc-400 dark:hover:text-zinc-100"
          )}
        >
          <Icon
            size={16}
            aria-hidden="true"
          />

          <span>
            {item.label}
          </span>
        </Link>
      );
    })}
  </nav>

  {/* =====================================================
      FOOTER
      ===================================================== */}

  <div className="border-t border-border p-4 text-[10px] text-muted">
    v0.2.0 · © Mukta Redij
  </div>
</aside>

);
}
