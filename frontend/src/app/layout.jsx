import { Inter } from "next/font/google";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";
import { ClientProviders } from "./providers";
import WebVitals from "@/components/WebVitals";
import "./globals.css";
import { jsx, jsxs } from "react/jsx-runtime";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const metadata = {
  title: "AI-Intelliview Orchestrator",
  description: "Distributed AI-powered interview orchestration dashboard",
};

function RootLayout({ children }) {
  return /* @__PURE__ */ jsx("html", {
    lang: "en",
    className: "dark",
    suppressHydrationWarning: true,
    children: /* @__PURE__ */ jsxs("body", {
      className: inter.variable + " font-sans",
      children: [
        /* Web Vitals Monitoring */
        /* @__PURE__ */ jsx(WebVitals, {}),

        /* @__PURE__ */ jsx("a", {
          href: "#main-content",
          className:
            "sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-[100] focus:rounded focus:bg-accent focus:px-3 focus:py-2 focus:text-sm focus:text-white",
          children: "Skip to main content",
        }),

        /* @__PURE__ */ jsx(ClientProviders, {
          children: /* @__PURE__ */ jsxs("div", {
            className: "flex min-h-screen bg-bg",
            children: [
              /* @__PURE__ */ jsx(Sidebar, {}),

              /* @__PURE__ */ jsxs("div", {
                className: "flex min-w-0 flex-1 flex-col",
                children: [
                  /* @__PURE__ */ jsx(Topbar, {}),

                  /* @__PURE__ */ jsx("main", {
                    id: "main-content",
                    tabIndex: -1,
                    className:
                      "flex-1 overflow-y-auto p-6 focus:outline-none",
                    children,
                  }),
                ],
              }),
            ],
          }),
        }),
      ],
    }),
  });
}

export { metadata };
export default RootLayout;
