import Link from "next/link";
import { jsx, jsxs } from "react/jsx-runtime";
function NotFound() {
  return /* @__PURE__ */ jsxs("div", { className: "mx-auto max-w-lg rounded-lg border border-border bg-bg-panel p-8 text-center", role: "alert", children: [
    /* @__PURE__ */ jsx("h2", { className: "text-xl font-semibold text-zinc-100", children: "404 \u2014 Page not found" }),
    /* @__PURE__ */ jsx("p", { className: "mt-2 text-sm text-muted", children: "The page you were looking for doesn't exist." }),
    /* @__PURE__ */ jsx(
      Link,
      {
        href: "/",
        className: "mt-4 inline-block rounded bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90",
        children: "Back to dashboard"
      }
    )
  ] });
}
export {
  NotFound as default
};
