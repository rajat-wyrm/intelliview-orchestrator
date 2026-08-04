"use client";

import { useEffect, useId, useState } from "react";
import { cn } from "@/lib/utils";

function Tooltip({
  content,
  children,
  side = "top",
  className,
}) {
  const [visible, setVisible] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const [wrapperRef, setWrapperRef] = useState(null);

  const tooltipId = useId();

  const updatePosition = () => {
    if (!wrapperRef) return;

    const rect = wrapperRef.getBoundingClientRect();
    const offset = 8;

    let top = 0;
    let left = 0;

    switch (side) {
      case "bottom":
        top = rect.bottom + offset;
        left = rect.left + rect.width / 2;
        break;

      case "right":
        top = rect.top + rect.height / 2;
        left = rect.right + offset;
        break;

      case "left":
        top = rect.top + rect.height / 2;
        left = rect.left - offset;
        break;

      default:
        top = rect.top - offset;
        left = rect.left + rect.width / 2;
    }

    setPosition({ top, left });
  };

  useEffect(() => {
    if (!visible) return;

    updatePosition();

    window.addEventListener("scroll", updatePosition, true);
    window.addEventListener("resize", updatePosition);

    return () => {
      window.removeEventListener("scroll", updatePosition, true);
      window.removeEventListener("resize", updatePosition);
    };
  }, [visible, side, wrapperRef]);

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key === "Escape") {
        setVisible(false);
      }
    };

    if (visible) {
      document.addEventListener("keydown", onKeyDown);
    }

    return () => {
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [visible]);

  return (
    <>
      <div
        ref={setWrapperRef}
        className="inline-block"
        aria-describedby={visible ? tooltipId : undefined}
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onFocus={() => setVisible(true)}
        onBlur={() => setVisible(false)}
      >
        {children}
      </div>

      {visible && (
        <div
          id={tooltipId}
          role="tooltip"
          aria-live="polite"
          className={cn(
            "pointer-events-none fixed z-50 rounded-md border border-border bg-bg-card px-2 py-1 text-xs text-white shadow-xl",
            "transition-opacity duration-150",
            side === "top" &&
              "-translate-x-1/2 -translate-y-full",
            side === "bottom" &&
              "-translate-x-1/2",
            side === "left" &&
              "-translate-x-full -translate-y-1/2",
            side === "right" &&
              "-translate-y-1/2",
            className
          )}
          style={{
            top: position.top,
            left: position.left,
          }}
        >
          {content}
        </div>
      )}
    </>
  );
}

export {
  Tooltip,
};