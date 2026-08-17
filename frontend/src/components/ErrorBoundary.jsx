"use client";
import { Component } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { jsx, jsxs } from "react/jsx-runtime";
class ErrorBoundary extends Component {
  state = { hasError: false, error: null };
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, info) {
    this.props.onError?.(error, info);
    console.error("[ErrorBoundary]", error, info);
  }
  reset = () => this.setState({ hasError: false, error: null });
  render() {
    if (!this.state.hasError) return this.props.children;
    if (this.props.fallback) return this.props.fallback;
    return /* @__PURE__ */ jsx("div", { className: "m-6 rounded-xl border border-rose-500/30 bg-rose-500/5 p-6", children: /* @__PURE__ */ jsxs("div", { className: "flex items-start gap-3", children: [
      /* @__PURE__ */ jsx("div", { className: "rounded-md bg-rose-500/10 p-2 text-rose-400", children: /* @__PURE__ */ jsx(AlertTriangle, { size: 20 }) }),
      /* @__PURE__ */ jsxs("div", { className: "min-w-0 flex-1", children: [
        /* @__PURE__ */ jsx("h2", { className: "text-sm font-semibold text-rose-200", children: "Something went wrong" }),
        /* @__PURE__ */ jsx("p", { className: "mt-1 text-xs text-rose-300/80", children: this.state.error?.message ?? "An unexpected error occurred." }),
        /* @__PURE__ */ jsxs(
          "button",
          {
            onClick: this.reset,
            className: "mt-3 inline-flex items-center gap-1.5 rounded-md border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs font-medium text-rose-200 hover:bg-rose-500/20",
            children: [
              /* @__PURE__ */ jsx(RefreshCw, { size: 12 }),
              " Try again"
            ]
          }
        )
      ] })
    ] }) });
  }
}
export {
  ErrorBoundary
};
