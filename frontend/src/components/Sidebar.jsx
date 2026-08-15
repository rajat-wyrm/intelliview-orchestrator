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
  Mail,
  GraduationCap
} from "lucide-react";
import { jsx, jsxs } from "react/jsx-runtime";
const items = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/interview", label: "Interview", icon: Video },
  { href: "/sessions", label: "Sessions", icon: Activity },
  { href: "/candidates", label: "Candidates", icon: UserCircle },
  { href: "/coaching", label: "Coaching", icon: GraduationCap },
  { href: "/workers", label: "Workers", icon: Users },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "http://localhost:8080", label: "Digest Control", icon: Mail, external: true }
];
function Sidebar({ mobile = false, onNavigate }) {
  const pathname = usePathname();
  return /* @__PURE__ */ jsxs("aside", { className: cn(
    mobile ? "flex w-full flex-col" : "hidden w-60 shrink-0 border-r border-border bg-bg-panel md:flex md:flex-col"
  ), children: [
    /* @__PURE__ */ jsxs("div", { className: "flex h-14 items-center gap-2 border-b border-border px-5", children: [
      /* @__PURE__ */ jsx("div", { className: "flex h-8 w-8 items-center justify-center rounded-md bg-accent text-white", children: /* @__PURE__ */ jsx(Shield, { size: 16 }) }),
      /* @__PURE__ */ jsxs("div", { children: [
        /* @__PURE__ */ jsx("div", { className: "text-sm font-semibold text-zinc-100", children: "AI-Intelliview" }),
        /* @__PURE__ */ jsx("div", { className: "text-[10px] uppercase tracking-wider text-muted", children: "Orchestrator" })
      ] })
    ] }),
    /* @__PURE__ */ jsx("nav", { className: "flex-1 space-y-0.5 p-3", children: items.map((it) => {
      const active = pathname === it.href || it.href !== "/" && pathname.startsWith(it.href);
      const linkProps = it.external ? {
        href: it.href,
        target: "_blank",
        rel: "noopener noreferrer",
        onClick: onNavigate,
        className: cn(
          "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition text-zinc-400 hover:bg-bg-card hover:text-zinc-100"
        )
      } : {
        href: it.href,
        onClick: onNavigate,
        className: cn(
          "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition",
          active ? "bg-accent/15 text-accent-light" : "text-zinc-400 hover:bg-bg-card hover:text-zinc-100"
        )
      };
      const content = [
        /* @__PURE__ */ jsx(it.icon, { size: 16 }),
        /* @__PURE__ */ jsx("span", { children: it.label })
      ];
      return it.external ? 
        /* @__PURE__ */ jsxs("a", { ...linkProps, children: content }, it.href) :
        /* @__PURE__ */ jsxs(Link, { ...linkProps, children: content }, it.href);
    }) }),
    /* @__PURE__ */ jsx("div", { className: "border-t border-border p-4 text-[10px] text-muted", children: "v0.2.0 \xB7 \xA9 Mukta Redij" })
  ] });
}
export {
  Sidebar
};