"use client";
import { useEffect } from "react";
import { useAppStore } from "@/lib/store";
function useHydrateToken() {
  const { hydrate, hasHydrated } = useAppStore();
  useEffect(() => {
    if (!hasHydrated) hydrate();
  }, [hydrate, hasHydrated]);
}
export {
  useHydrateToken
};
