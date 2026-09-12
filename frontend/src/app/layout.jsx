import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";
import Providers from "./providers";
import WebVitals from "@/components/WebVitals";
import "./globals.css";

const fontClassName = "font-sans";

export const metadata = {
  title: "AI-Intelliview Orchestrator",
  description: "Distributed AI-powered interview orchestration dashboard",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={fontClassName}>
        <WebVitals />
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-[100] focus:rounded focus:bg-accent focus:px-3 focus:py-2 focus:text-sm focus:text-white"
        >
          Skip to main content
        </a>
        <Providers>
          <div className="flex min-h-screen bg-bg">
            <Sidebar />
            <div className="flex min-w-0 flex-1 flex-col">
              <Topbar />
              <main
                id="main-content"
                tabIndex={-1}
                className="flex-1 overflow-y-auto p-6 focus:outline-none"
              >
                {children}
              </main>
            </div>
          </div>
        </Providers>
      </body>
    </html>
  );
}
