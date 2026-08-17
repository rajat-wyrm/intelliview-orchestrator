"use client";
import { create } from "zustand";
const STORAGE_KEY = "app_theme";
function readStored() {
  if (typeof window === "undefined") return "dark";
  const v = localStorage.getItem(STORAGE_KEY);
  if (v === "dark" || v === "light" || v === "system") return v;
  return "dark";
}
function resolve(theme) {
  if (theme !== "system") return theme;
  if (typeof window === "undefined") return "dark";
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}
function apply(resolved) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.classList.toggle("dark", resolved === "dark");
  root.classList.toggle("light", resolved === "light");
  root.style.colorScheme = resolved;
}
const useThemeStore = create((set, get) => ({
  theme: "dark",
  resolved: "dark",
  setTheme: (t) => {
    const r = resolve(t);
    try {
      localStorage.setItem(STORAGE_KEY, t);
    } catch {
    }
    apply(r);
    set({ theme: t, resolved: r });
  },
  cycle: () => {
    const cur = get().theme;
    const next = cur === "dark" ? "light" : cur === "light" ? "system" : "dark";
    get().setTheme(next);
  }
}));
function hydrateTheme() {
  const theme = readStored();
  const resolved = resolve(theme);
  apply(resolved);
  useThemeStore.setState({ theme, resolved });
  if (typeof window !== "undefined") {
    const mq = window.matchMedia("(prefers-color-scheme: light)");
    mq.addEventListener?.("change", () => {
      if (useThemeStore.getState().theme === "system") {
        const r = resolve("system");
        apply(r);
        useThemeStore.setState({ resolved: r });
      }
    });
  }
}
export {
  hydrateTheme,
  useThemeStore
};
