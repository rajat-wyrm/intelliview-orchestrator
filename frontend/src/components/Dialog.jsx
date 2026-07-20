"use client";

import {
AnimatePresence,
motion,
useReducedMotion,
} from "framer-motion";
import { X } from "lucide-react";
import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

const FOCUSABLE_SELECTOR =
'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function Dialog({
open,
onOpenChange,
children,
}) {
const containerRef = useRef(null);
const previousActiveRef = useRef(null);
const reduceMotion = useReducedMotion();

useEffect(() => {
if (!open) {
return;
}


/*
 * Remember the element that had focus before the dialog
 * opened so focus can be restored when it closes.
 */
previousActiveRef.current = document.activeElement ?? null;

const handleKeyDown = (event) => {
  /*
   * Close the dialog when Escape is pressed.
   */
  if (event.key === "Escape") {
    onOpenChange(false);
    return;
  }

  /*
   * Keep keyboard focus inside the dialog.
   */
  if (
    event.key !== "Tab" ||
    !containerRef.current
  ) {
    return;
  }

  const focusableElements = Array.from(
    containerRef.current.querySelectorAll(
      FOCUSABLE_SELECTOR
    )
  ).filter(
    (element) =>
      !element.hasAttribute("aria-hidden")
  );

  if (focusableElements.length === 0) {
    event.preventDefault();
    return;
  }

  const firstElement = focusableElements[0];
  const lastElement =
    focusableElements[
      focusableElements.length - 1
    ];

  const activeElement = document.activeElement;

  if (
    event.shiftKey &&
    (activeElement === firstElement ||
      !containerRef.current.contains(
        activeElement
      ))
  ) {
    event.preventDefault();
    lastElement.focus();
  } else if (
    !event.shiftKey &&
    activeElement === lastElement
  ) {
    event.preventDefault();
    firstElement.focus();
  }
};

document.addEventListener(
  "keydown",
  handleKeyDown
);

/*
 * Prevent the page behind the dialog from scrolling.
 */
const previousOverflow =
  document.body.style.overflow;

document.body.style.overflow = "hidden";

/*
 * Move focus to the first interactive element.
 */
const focusableElements =
  containerRef.current?.querySelectorAll(
    FOCUSABLE_SELECTOR
  );

const initialElement = focusableElements
  ? Array.from(focusableElements).find(
      (element) =>
        !element.hasAttribute("aria-hidden")
    )
  : null;

initialElement?.focus();

return () => {
  document.removeEventListener(
    "keydown",
    handleKeyDown
  );

  document.body.style.overflow =
    previousOverflow;

  /*
   * Restore focus to the element that opened the dialog.
   */
  previousActiveRef.current?.focus?.();
};


}, [open, onOpenChange]);

return ( <AnimatePresence>
{open && (
<motion.div
role="dialog"
aria-modal="true"
ref={containerRef}
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
duration: reduceMotion ? 0 : 0.15,
}}
className={cn(
"fixed inset-0 z-50",
"flex items-start justify-center",
"bg-black/50 dark:bg-black/60",
"p-4 pt-[12vh]",
"backdrop-blur-sm"
)}
onClick={() => onOpenChange(false)}
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
? { opacity: 1 }
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
transition={
reduceMotion
? { duration: 0 }
: {
type: "spring",
stiffness: 400,
damping: 30,
}
}
onClick={(event) =>
event.stopPropagation()
}
className="w-full"
>
{children}
</motion.div>
</motion.div>
)} </AnimatePresence>
);
}

export function DialogContent({
children,
className,
onClose,
}) {
return (
<div
className={cn(
"relative rounded-xl",
"border border-border",
"bg-bg-panel",
"text-zinc-900 dark:text-zinc-100",
"shadow-2xl",
"transition-colors duration-200",
className
)}
>
{onClose && (
<button
type="button"
onClick={onClose}
className={cn(
"absolute right-3 top-3 z-10",
"rounded-md p-1.5",
"text-muted",
"hover:bg-bg-card",
"hover:text-zinc-900 dark:hover:text-zinc-100",
"focus-visible:outline-none",
"focus-visible:ring-2",
"focus-visible:ring-accent/70"
)}
aria-label="Close dialog"
> <X
         size={16}
         aria-hidden="true"
       /> </button>
)}


  {children}
</div>

);
}

export function DialogTitle({
children,
className,
}) {
return (
<h2
className={cn(
"text-base font-semibold",
"text-zinc-900 dark:text-zinc-100",
className
)}
>
{children} </h2>
);
}
