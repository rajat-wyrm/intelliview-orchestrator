"use client";

import {
Suspense,
lazy,
useEffect,
useState,
useCallback,
} from "react";
import { SWRConfig } from "swr";
import { usePathname, useRouter } from "next/navigation";

import { swrFetcher } from "@/lib/fetcher";
import { useHydrateToken } from "@/hooks/useHydrateToken";
import { hydrateTheme } from "@/lib/theme";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useKeyboardNav } from "@/hooks/useKeyboardNav";
import { useUIStore } from "@/lib/ui-store";
import { endpoints, api } from "@/lib/api";
import { toast } from "@/lib/toast";

const CommandPalette = lazy(() =>
import("@/components/CommandPalette").then((m) => ({
default: m.CommandPalette,
}))
);

const Toaster = lazy(() =>
import("@/components/Toaster").then((m) => ({
default: m.Toaster,
}))
);

const ShortcutsHelp = lazy(() =>
import("@/components/ShortcutsHelp").then((m) => ({
default: m.ShortcutsHelp,
}))
);

const MobileSidebar = lazy(() =>
import("@/components/MobileSidebar").then((m) => ({
default: m.MobileSidebar,
}))
);

const SidebarMobile = lazy(() =>
import("@/components/Sidebar").then((m) => ({
default: m.Sidebar,
}))
);

const ScreenLock = lazy(() =>
import("@/components/ScreenLock").then((m) => ({
default: m.default,
}))
);

function NullFallback() {
return null;
}

function ScreenLockWrapper() {
const [isLocked, setIsLocked] = useState(false);

useEffect(() => {
const stored = localStorage.getItem("intelliview_screen_lock");


if (stored === "locked") {
  setIsLocked(true);
}

const interval = setInterval(() => {
  if (
    localStorage.getItem("intelliview_screen_lock") === "locked"
  ) {
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

return ( <ScreenLock
   isLocked={isLocked}
   onUnlock={handleUnlock}
 />
);
}

export function ClientProviders({ children }) {
useHydrateToken();

const [paletteOpen, setPaletteOpen] = useState(false);
const [helpOpen, setHelpOpen] = useState(false);

const router = useRouter();
const pathname = usePathname();

const mobileOpen = useUIStore(
(state) => state.mobileSidebarOpen
);

const setMobileOpen = useUIStore(
(state) => state.setMobileSidebar
);

/*

* Restore the user's saved theme when the client application
* is mounted.
*
* hydrateTheme() reads the stored theme from localStorage and
* applies either the "dark" or "light" class to the root
* <html> element.

*/
useEffect(() => {
hydrateTheme();
}, []);

useKeyboardNav(() => setHelpOpen(true));

/*

* Command palette keyboard shortcut.
*
* macOS: Cmd + K
* Windows/Linux: Ctrl + K
  */
  useEffect(() => {
  const onKey = (event) => {
  if (
  (event.metaKey || event.ctrlKey) &&
  event.key.toLowerCase() === "k"
  ) {
  event.preventDefault();

  setPaletteOpen((open) => !open);
  }
  };


document.addEventListener("keydown", onKey);



return () => {
  document.removeEventListener("keydown", onKey);
};


}, []);

/*

* Close the mobile sidebar whenever navigation occurs.
  */
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
      const result = await endpoints.detectFailures();

      toast.success(
        "Detection complete",
        `${result.failed_sessions_detected} failed · ${result.unhealthy_workers_detected} unhealthy · ${result.stuck_sessions_detected} stuck`
      );
    } catch (error) {
      toast.error(
        "Detection failed",
        error instanceof Error
          ? error.message
          : String(error)
      );
    }

    return;
  }

  if (action === "clear-cache") {
    try {
      await api.delete("/clear-cache");

      toast.success("Cache cleared");
    } catch (error) {
      toast.error(
        "Failed to clear cache",
        error instanceof Error
          ? error.message
          : String(error)
      );
    }

    return;
  }
},
[router]


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


    onError: (error) => {
      console.warn("[SWR]", error.message);
    },
  }}
>
  <ErrorBoundary>
    {children}
  </ErrorBoundary>

  <Suspense fallback={null}>
    <ScreenLockWrapper />
  </Suspense>

  <Suspense fallback={null}>
    <CommandPalette
      open={paletteOpen}
      onOpenChange={setPaletteOpen}
      onAction={handleAction}
    />

    <ShortcutsHelp
      open={helpOpen}
      onClose={() => setHelpOpen(false)}
    />

    <Toaster />

    <MobileSidebar
      open={mobileOpen}
      onClose={() => setMobileOpen(false)}
    >
      <Suspense fallback={<NullFallback />}>
        <SidebarMobile
          mobile
          onNavigate={() => setMobileOpen(false)}
        />
      </Suspense>
    </MobileSidebar>
  </Suspense>
</SWRConfig>

);
}
