"use client";
import { create } from "zustand";
const useToastStore = create((set) => ({
  toasts: [],
  push: (t) => {
    const id = Math.random().toString(36).slice(2, 9);
    set((s) => ({ toasts: [...s.toasts, { id, ...t }] }));
    const duration = t.duration ?? 4e3;
    if (duration > 0) setTimeout(() => useToastStore.getState().dismiss(id), duration);
    return id;
  },
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
  clear: () => set({ toasts: [] })
}));
const toast = {
  success: (title, description) => useToastStore.getState().push({ title, description, variant: "success" }),
  error: (title, description) => useToastStore.getState().push({ title, description, variant: "error" }),
  info: (title, description) => useToastStore.getState().push({ title, description, variant: "info" }),
  warn: (title, description) => useToastStore.getState().push({ title, description, variant: "warn" })
};
export {
  toast,
  useToastStore
};
