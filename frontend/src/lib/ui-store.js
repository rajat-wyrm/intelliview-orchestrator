import { create } from "zustand";
const useUIStore = create((set) => ({
  mobileSidebarOpen: false,
  setMobileSidebar: (open) => set({ mobileSidebarOpen: open })
}));
export {
  useUIStore
};
