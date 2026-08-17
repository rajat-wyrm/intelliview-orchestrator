"use client";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useEffect } from "react";
import { cn } from "@/lib/utils";
import { Fragment, jsx, jsxs } from "react/jsx-runtime";
function MobileSidebar({ open, onClose, children }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  return /* @__PURE__ */ jsx(AnimatePresence, { children: open && /* @__PURE__ */ jsxs(Fragment, { children: [
    /* @__PURE__ */ jsx(
      motion.div,
      {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        exit: { opacity: 0 },
        transition: { duration: 0.2 },
        className: "fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden",
        onClick: onClose,
        "aria-hidden": true
      }
    ),
    /* @__PURE__ */ jsxs(
      motion.aside,
      {
        initial: { x: "-100%" },
        animate: { x: 0 },
        exit: { x: "-100%" },
        transition: { type: "spring", stiffness: 400, damping: 40 },
        className: cn(
          "fixed inset-y-0 left-0 z-50 w-72 border-r border-border bg-bg-panel shadow-2xl md:hidden"
        ),
        children: [
          /* @__PURE__ */ jsx(
            "button",
            {
              onClick: onClose,
              className: "absolute right-3 top-3 z-10 rounded-md p-1.5 text-muted hover:bg-bg-card hover:text-zinc-200",
              "aria-label": "Close menu",
              children: /* @__PURE__ */ jsx(X, { size: 16 })
            }
          ),
          children
        ]
      }
    )
  ] }) });
}
export {
  MobileSidebar
};
