import { create } from "zustand";
import { api } from "./api";
const useAppStore = create((set) => ({
  token: null,
  hasHydrated: false,
  setToken: (token) => {
    api.setToken(token);
    set({ token });
  },
  hydrate: () => {
    const t = api.loadToken();
    set({ token: t, hasHydrated: true });
  }
}));
export {
  useAppStore
};
