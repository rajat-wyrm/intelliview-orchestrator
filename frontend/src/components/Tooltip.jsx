"use client";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { Fragment, jsx, jsxs } from "react/jsx-runtime";
function Tooltip({ content, children, side = "top", className }) {
  const [visible, setVisible] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const [wrapperRef, setWrapperRef] = useState(null);
  useEffect(() => {
    if (!visible || !wrapperRef) return;
    const rect = wrapperRef.getBoundingClientRect();
    const offset = 8;
    let top = 0;
    let left = 0;
    if (side === "top") {
      top = rect.top - offset;
      left = rect.left + rect.width / 2;
    } else if (side === "bottom") {
      top = rect.bottom + offset;
      left = rect.left + rect.width / 2;
    } else if (side === "right") {
      top = rect.top + rect.height / 2;
      left = rect.right + offset;
    } else {
      top = rect.top + rect.height / 2;
      left = rect.left - offset;
    }
    setPosition({ top, left });
  }, [visible, side, wrapperRef]);
  return /* @__PURE__ */ jsxs(Fragment, { children: [
    /* @__PURE__ */ jsx(
      "div",
      {
        ref: setWrapperRef,
        onMouseEnter: () => setVisible(true),
        onMouseLeave: () => setVisible(false),
        onFocus: () => setVisible(true),
        onBlur: () => setVisible(false),
        className: "inline-block",
        children
      }
    ),
    visible && /* @__PURE__ */ jsx(
      "div",
      {
        role: "tooltip",
        className: cn(
          "pointer-events-none fixed z-50 -translate-x-1/2 -translate-y-1/2 rounded-md border border-border bg-bg-card px-2 py-1 text-xs text-zinc-200 shadow-lg",
          side === "right" && "translate-x-0 translate-y-0",
          side === "left" && "translate-x-0 translate-y-0",
          side === "left" || side === "right" ? "-translate-y-1/2" : "-translate-x-1/2 -translate-y-full",
          side === "bottom" && "translate-x-0 -translate-y-0",
          side === "right" && "translate-x-0 -translate-y-1/2",
          side === "left" && "-translate-x-full -translate-y-1/2",
          className
        ),
        style: side === "top" ? { top: position.top, left: position.left } : side === "bottom" ? { top: position.top, left: position.left } : side === "right" ? { top: position.top, left: position.left } : { top: position.top, left: position.left },
        children: content
      }
    )
  ] });
}
export {
  Tooltip
};
