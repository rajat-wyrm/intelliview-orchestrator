"use client";
/**
 * Reusable Modal/Dialog component.
 * Used in: CommandPalette.jsx, SessionDetail.jsx, ShortcutsHelp.jsx
 */
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { X } from "lucide-react";
import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

const FOCUSABLE_SELECTOR =
  'a[href],button:not([disabled]),textarea:not([disabled]),input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])';

/**
 * Dialog — animated, accessible modal container.
 *
 * @param {boolean} open
 * @param {function} onOpenChange — called with `false` on backdrop click / Escape
 * @param {React.ReactNode} children — should contain a <DialogContent>
 *
 * @example
 * <Dialog open={open} onOpenChange={setOpen}>
 *   <DialogContent onClose={() => setOpen(false)}>
 *     <DialogTitle>My Modal</DialogTitle>
 *     <p>Content here.</p>
 *   </DialogContent>
 * </Dialog>
 */
function Dialog({ open, onOpenChange, children }) {
  const containerRef = useRef(null);
  const previousActiveRef = useRef(null);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (!open) return;
    previousActiveRef.current = document.activeElement ?? null;

    const onKey = (e) => {
      if (e.key === "Escape") {
        onOpenChange(false);
        return;
      }
      if (e.key !== "Tab" || !containerRef.current) return;
      const focusables = Array.from(
        containerRef.current.querySelectorAll(FOCUSABLE_SELECTOR)
      ).filter((el) => !el.hasAttribute("aria-hidden"));
      if (focusables.length === 0) { e.preventDefault(); return; }
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement;
      if (e.shiftKey && (active === first || !containerRef.current.contains(active))) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";

    const initial = Array.from(
      containerRef.current?.querySelectorAll(FOCUSABLE_SELECTOR) ?? []
    ).find((el) => !el.hasAttribute("aria-hidden"));
    initial?.focus();

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      previousActiveRef.current?.focus?.();
    };
  }, [open, onOpenChange]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          role="dialog"
          aria-modal="true"
          ref={containerRef}
          initial={reduceMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={reduceMotion ? undefined : { opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 p-4 pt-[12vh] backdrop-blur-sm"
          onClick={() => onOpenChange(false)}
        >
          <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: -20, scale: 0.96 }}
            animate={reduceMotion ? { opacity: 1 } : { opacity: 1, y: 0, scale: 1 }}
            exit={reduceMotion ? undefined : { opacity: 0, y: -20, scale: 0.96 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full"
          >
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/**
 * DialogContent — the panel rendered inside the Dialog backdrop.
 *
 * @param {function} onClose — if provided, renders an ✕ close button
 */
function DialogContent({ children, className, onClose }) {
  return (
    <div
      className={cn(
        "relative rounded-xl border border-border bg-bg-panel shadow-2xl",
        className
      )}
    >
      {onClose && (
        <button
          onClick={onClose}
          className="absolute right-3 top-3 z-10 rounded p-1 text-muted hover:bg-bg-card hover:text-zinc-200 transition-colors"
          aria-label="Close"
        >
          <X size={16} />
        </button>
      )}
      {children}
    </div>
  );
}

/**
 * DialogTitle — styled heading for the dialog.
 */
function DialogTitle({ children, className }) {
  return (
    <h2 className={cn("text-base font-semibold text-zinc-100", className)}>
      {children}
    </h2>
  );
}

export { Dialog, DialogContent, DialogTitle };
