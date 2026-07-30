"use client";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X } from "lucide-react";
import { useToastStore } from "@/lib/toast";
import { cn } from "@/lib/utils";
import { jsx, jsxs } from "react/jsx-runtime";
const ICONS = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
  warn: AlertTriangle
};
const STYLES = {
  success: "border-emerald-500/30 bg-emerald-500/10 text-zinc-200",
  error: "border-rose-500/30 bg-rose-500/10 text-zinc-200",
  info: "border-indigo-500/30 bg-indigo-500/10 text-zinc-200",
  warn: "border-amber-500/30 bg-amber-500/10 text-zinc-200"
};
const ICON_STYLES = {
  success: "text-emerald-400",
  error: "text-rose-400",
  info: "text-indigo-400",
  warn: "text-amber-400"
};
function ToastItem({ toast }) {
  const Icon = ICONS[toast.variant];
  const dismiss = useToastStore((s) => s.dismiss);
  return /* @__PURE__ */ jsxs(
    motion.div,
    {
      layout: true,
      initial: { opacity: 0, y: 20, scale: 0.95 },
      animate: { opacity: 1, y: 0, scale: 1 },
      exit: { opacity: 0, x: 100, scale: 0.95 },
      transition: { type: "spring", stiffness: 500, damping: 40 },
      className: cn(
        "pointer-events-auto flex w-full items-start gap-3 rounded-lg border px-4 py-3 shadow-lg backdrop-blur",
        STYLES[toast.variant]
      ),
      children: [
        /* @__PURE__ */ jsx(Icon, { size: 18, className: cn("mt-0.5 shrink-0", ICON_STYLES[toast.variant]) }),
        /* @__PURE__ */ jsxs("div", { className: "min-w-0 flex-1", children: [
          /* @__PURE__ */ jsx("div", { className: "text-sm font-medium", children: toast.title }),
          toast.description && /* @__PURE__ */ jsx("div", { className: "mt-0.5 text-xs opacity-80", children: toast.description })
        ] }),
        /* @__PURE__ */ jsx(
          "button",
          {
            onClick: () => dismiss(toast.id),
            className: "shrink-0 rounded p-0.5 opacity-60 hover:opacity-100",
            "aria-label": "Dismiss",
            children: /* @__PURE__ */ jsx(X, { size: 14 })
          }
        )
      ]
    }
  );
}
function Toaster() {
  const toasts = useToastStore((s) => s.toasts);
  return /* @__PURE__ */ jsx("div", { className: "pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2", children: /* @__PURE__ */ jsx(AnimatePresence, { children: toasts.map((t) => /* @__PURE__ */ jsx(ToastItem, { toast: t }, t.id)) }) });
}
export {
  Toaster
};
