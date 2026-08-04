"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { X } from "lucide-react";
import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { jsx, jsxs } from "react/jsx-runtime";

const FOCUSABLE_SELECTOR =
  'a[href],button:not([disabled]),textarea:not([disabled]),input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])';

function Dialog({
  open,
  onOpenChange,
  children,
  labelledBy,
  describedBy,
}) {
  const containerRef = useRef(null);
  const previousActiveRef = useRef(null);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (!open) return;

    previousActiveRef.current = document.activeElement ?? null;

    const onKey = (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onOpenChange(false);
        return;
      }

      if (e.key !== "Tab" || !containerRef.current) return;

      const focusables = Array.from(
        containerRef.current.querySelectorAll(FOCUSABLE_SELECTOR)
      ).filter((el) => !el.hasAttribute("aria-hidden"));

      if (focusables.length === 0) {
        e.preventDefault();
        containerRef.current.focus();
        return;
      }

      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement;

      if (
        e.shiftKey &&
        (active === first || !containerRef.current.contains(active))
      ) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";

    requestAnimationFrame(() => {
      const focusables = containerRef.current?.querySelectorAll(
        FOCUSABLE_SELECTOR
      );

      const initial = focusables
        ? Array.from(focusables).find((el) => !el.hasAttribute("aria-hidden"))
        : null;

      if (initial) {
        initial.focus();
      } else {
        containerRef.current?.focus();
      }
    });

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      previousActiveRef.current?.focus?.();
    };
  }, [open, onOpenChange]);

  const motionProps = reduceMotion
    ? {
        initial: false,
        animate: undefined,
        exit: undefined,
        transition: { duration: 0 },
      }
    : {};

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          role="dialog"
          aria-modal="true"
          aria-labelledby={labelledBy}
          aria-describedby={describedBy}
          tabIndex={-1}
          ref={containerRef}
          initial={reduceMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={reduceMotion ? undefined : { opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 p-4 pt-[12vh] backdrop-blur-sm"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              onOpenChange(false);
            }
          }}
        >
          <motion.div
            initial={
              reduceMotion
                ? false
                : {
                    opacity: 0,
                    y: -20,
                    scale: 0.96,
                  }
            }
            animate={
              reduceMotion
                ? {
                    opacity: 1,
                  }
                : {
                    opacity: 1,
                    y: 0,
                    scale: 1,
                  }
            }
            exit={
              reduceMotion
                ? undefined
                : {
                    opacity: 0,
                    y: -20,
                    scale: 0.96,
                  }
            }
            transition={{
              type: "spring",
              stiffness: 400,
              damping: 30,
            }}
            onClick={(e) => e.stopPropagation()}
            className="w-full"
            {...motionProps}
          >
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

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
          type="button"
          onClick={onClose}
          aria-label="Close dialog"
          className="absolute right-3 top-3 z-10 rounded-md p-2 text-zinc-300 transition-colors hover:bg-bg-card hover:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-bg-panel"
        >
          <X size={18} />
        </button>
      )}

      {children}
    </div>
  );
}

function DialogTitle({
  children,
  className,
  id = "dialog-title",
}) {
  return (
    <h2
      id={id}
      className={cn(
        "text-base font-semibold text-zinc-100",
        className
      )}
    >
      {children}
    </h2>
  );
}

export {
  Dialog,
  DialogContent,
  DialogTitle,
};