"use client";
import { Suspense, lazy, useEffect, useState, useCallback } from "react";
import { SWRConfig } from "swr";
import { swrFetcher } from "@/lib/fetcher";
import { useHydrateToken } from "@/hooks/useHydrateToken";
import { hydrateTheme } from "@/lib/theme";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useKeyboardNav } from "@/hooks/useKeyboardNav";
import { useUIStore } from "@/lib/ui-store";
import { endpoints, api } from "@/lib/api";
import { usePathname, useRouter } from "next/navigation";
import { toast } from "@/lib/toast";

const CommandPalette = lazy(() =>
  import("@/components/CommandPalette").then((m) => ({ default: m.CommandPalette })),
);
const Toaster = lazy(() =>
  import("@/components/Toaster").then((m) => ({ default: m.Toaster })),
);
const ShortcutsHelp = lazy(() =>
  import("@/components/ShortcutsHelp").then((m) => ({ default: m.ShortcutsHelp })),
);
const MobileSidebar = lazy(() =>
  import("@/components/MobileSidebar").then((m) => ({ default: m.MobileSidebar })),
);
const SidebarMobile = lazy(() =>
  import("@/components/Sidebar").then((m) => ({ default: m.Sidebar })),
);
const ScreenLock = lazy(() =>
  import("@/components/ScreenLock").then((m) => ({ default: m.default })),
);

function NullFallback() {
  return null;
}

function ScreenLockWrapper() {
  const [isLocked, setIsLocked] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("intelliview_screen_lock");
    if (stored === "locked") setIsLocked(true);

    const interval = setInterval(() => {
      if (localStorage.getItem("intelliview_screen_lock") === "locked") {
        setIsLocked(true);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleUnlock = useCallback((pin) => {
    if (pin === "1234") {
      setIsLocked(false);
      localStorage.removeItem("intelliview_screen_lock");
      return true;
    }
    return false;
  }, []);

  return <ScreenLock isLocked={isLocked} onUnlock={handleUnlock} />;
}

export function ClientProviders({ children }) {
  useHydrateToken();
  useEffect(() => {
    hydrateTheme();
  }, []);

  const [paletteOpen, setPaletteOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const router = useRouter();
  const pathname = usePathname();
  const mobileOpen = useUIStore((s) => s.mobileSidebarOpen);
  const setMobileOpen = useUIStore((s) => s.setMobileSidebar);

  useKeyboardNav(() => setHelpOpen(true));

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname, setMobileOpen]);

  const handleAction = useCallback(
    async (action) => {
      if (action === "start") {
        router.push("/sessions?action=start");
        return;
      }
      if (action === "live-interview") {
        router.push("/interview");
        return;
      }
      if (action === "refresh") {
        toast.info("Refreshing all data...");
        window.location.reload();
        return;
      }
      if (action === "detect") {
        try {
          const r = await endpoints.detectFailures();
          toast.success(
            "Detection complete",
            `${r.failed_sessions_detected} failed · ${r.unhealthy_workers_detected} unhealthy · ${r.stuck_sessions_detected} stuck`,
          );
        } catch (e) {
          toast.error("Detection failed", e instanceof Error ? e.message : String(e));
        }
        return;
      }
      if (action === "clear-cache") {
        try {
          await api.delete("/clear-cache");
          toast.success("Cache cleared");
        } catch (e) {
          toast.error("Failed to clear cache", e instanceof Error ? e.message : String(e));
        }
        return;
      }
    },
    [router],
  );

  return (
    <SWRConfig
      value={{
        fetcher: swrFetcher,
        revalidateOnFocus: true,
        refreshInterval: 5000,
        shouldRetryOnError: false,
        dedupingInterval: 2000,
        errorRetryInterval: 8000,
        onError: (err) => {
          console.warn("[SWR]", err.message);
        },
      }}
    >
      <ErrorBoundary>{children}</ErrorBoundary>
      <Suspense fallback={null}>
        <ScreenLockWrapper />
      </Suspense>
      <Suspense fallback={null}>
        <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} onAction={handleAction} />
        <ShortcutsHelp open={helpOpen} onClose={() => setHelpOpen(false)} />
        <Toaster />
        <MobileSidebar open={mobileOpen} onClose={() => setMobileOpen(false)}>
          <Suspense fallback={<NullFallback />}>
            <SidebarMobile mobile onNavigate={() => setMobileOpen(false)} />
          </Suspense>
        </MobileSidebar>
      </Suspense>
    </SWRConfig>
  );
}
