"use client";
import { cn } from "@/lib/utils";
import { jsx, jsxs } from "react/jsx-runtime";
function IllustrationEmpty({ className }) {
  return /* @__PURE__ */ jsxs(
    "svg",
    {
      viewBox: "0 0 200 140",
      className: cn("h-32 w-48 text-muted", className),
      fill: "none",
      stroke: "currentColor",
      strokeWidth: "1.5",
      children: [
        /* @__PURE__ */ jsx("rect", { x: "30", y: "20", width: "140", height: "100", rx: "8", strokeOpacity: "0.4" }),
        /* @__PURE__ */ jsx("line", { x1: "50", y1: "50", x2: "150", y2: "50", strokeOpacity: "0.3" }),
        /* @__PURE__ */ jsx("line", { x1: "50", y1: "70", x2: "130", y2: "70", strokeOpacity: "0.3" }),
        /* @__PURE__ */ jsx("line", { x1: "50", y1: "90", x2: "120", y2: "90", strokeOpacity: "0.3" }),
        /* @__PURE__ */ jsx("circle", { cx: "100", cy: "105", r: "14", strokeOpacity: "0.5" }),
        /* @__PURE__ */ jsx("path", { d: "M 94 105 L 100 99 L 106 105 L 100 111 Z", fill: "currentColor", stroke: "none", opacity: "0.6" })
      ]
    }
  );
}
function IllustrationError({ className }) {
  return /* @__PURE__ */ jsxs(
    "svg",
    {
      viewBox: "0 0 200 140",
      className: cn("h-32 w-48 text-rose-400/70", className),
      fill: "none",
      stroke: "currentColor",
      strokeWidth: "1.5",
      children: [
        /* @__PURE__ */ jsx("circle", { cx: "100", cy: "70", r: "40", strokeOpacity: "0.4" }),
        /* @__PURE__ */ jsx("line", { x1: "100", y1: "50", x2: "100", y2: "80", strokeOpacity: "0.7" }),
        /* @__PURE__ */ jsx("circle", { cx: "100", cy: "92", r: "2", fill: "currentColor" })
      ]
    }
  );
}
export {
  IllustrationEmpty,
  IllustrationError
};
