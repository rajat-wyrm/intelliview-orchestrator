"use client";

import {
AnimatePresence,
motion,
useReducedMotion,
} from "framer-motion";
import { X } from "lucide-react";
import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";

export function MobileSidebar({
open,
onClose,
children,
}) {
const sidebarRef = useRef(null);
const closeButtonRef = useRef(null);
const previousActiveRef = useRef(null);
const reduceMotion = useReducedMotion();

useEffect(() => {
if (!open) {
return;
}


/*
 * Remember the previously focused element so keyboard
 * focus can be restored when the sidebar closes.
 */
previousActiveRef.current =
  document.activeElement;

/*
 * Prevent the page behind the mobile navigation
 * from scrolling while the drawer is open.
 */
const previousOverflow =
  document.body.style.overflow;

document.body.style.overflow = "hidden";

/*
 * Move keyboard focus to the close button.
 */
requestAnimationFrame(() => {
  closeButtonRef.current?.focus();
});

const handleKeyDown = (event) => {
  if (event.key === "Escape") {
    onClose();
  }
};

document.addEventListener(
  "keydown",
  handleKeyDown
);

return () => {
  document.removeEventListener(
    "keydown",
    handleKeyDown
  );

  document.body.style.overflow =
    previousOverflow;

  /*
   * Restore focus to the element that opened
   * the mobile sidebar.
   */
  previousActiveRef.current?.focus?.();
};


}, [open, onClose]);

return ( <AnimatePresence>
{open && (
<>
{/* ===============================================
BACKDROP
=============================================== */}


      <motion.div
        initial={
          reduceMotion
            ? false
            : { opacity: 0 }
        }
        animate={{ opacity: 1 }}
        exit={
          reduceMotion
            ? undefined
            : { opacity: 0 }
        }
        transition={{
          duration: reduceMotion
            ? 0
            : 0.2,
        }}
        className={cn(
          "fixed inset-0 z-40 md:hidden",
          "bg-black/40 dark:bg-black/60",
          "backdrop-blur-sm"
        )}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* ===============================================
          MOBILE SIDEBAR
          =============================================== */}

      <motion.aside
        ref={sidebarRef}
        initial={
          reduceMotion
            ? false
            : { x: "-100%" }
        }
        animate={{ x: 0 }}
        exit={
          reduceMotion
            ? undefined
            : { x: "-100%" }
        }
        transition={
          reduceMotion
            ? { duration: 0 }
            : {
                type: "spring",
                stiffness: 400,
                damping: 40,
              }
        }
        className={cn(
          "fixed inset-y-0 left-0 z-50",
          "w-72 max-w-[85vw]",
          "border-r border-border",
          "bg-bg-panel",
          "text-zinc-900 dark:text-zinc-100",
          "shadow-2xl",
          "md:hidden"
        )}
        role="dialog"
        aria-modal="true"
        aria-label="Mobile navigation"
      >
        {/* Close button */}

        <button
          ref={closeButtonRef}
          type="button"
          onClick={onClose}
          className={cn(
            "absolute right-3 top-3 z-10",
            "rounded-md p-1.5",
            "text-muted",
            "transition-colors",
            "hover:bg-bg-card",
            "hover:text-zinc-900",
            "dark:hover:text-zinc-100",
            "focus-visible:outline-none",
            "focus-visible:ring-2",
            "focus-visible:ring-accent/70"
          )}
          aria-label="Close navigation menu"
        >
          <X
            size={16}
            aria-hidden="true"
          />
        </button>

        {children}
      </motion.aside>
    </>
  )}
</AnimatePresence>
);
}
