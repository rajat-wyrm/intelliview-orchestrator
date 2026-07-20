"use client";

import { create } from "zustand";

const STORAGE_KEY = "app_theme";
const DEFAULT_THEME = "dark";

/**

* Read the user's saved theme preference.
* Falls back to dark mode if no valid preference exists.
  */
  function readStoredTheme() {
  if (typeof window === "undefined") {
  return DEFAULT_THEME;
  }

try {
const storedTheme = localStorage.getItem(STORAGE_KEY);


if (storedTheme === "dark" || storedTheme === "light") {
  return storedTheme;
}

} catch {
// localStorage may be unavailable in some browser environments.
}

return DEFAULT_THEME;
}

/**

* Apply the selected theme globally to the document.
  */
  function applyTheme(theme) {
  if (typeof document === "undefined") {
  return;
  }

const root = document.documentElement;

root.classList.toggle("dark", theme === "dark");
root.classList.toggle("light", theme === "light");

root.style.colorScheme = theme;
}

/**

* Zustand theme store.
*
* The application currently requires two themes:
* * dark
* * light
    */
    const useThemeStore = create((set, get) => ({
    theme: DEFAULT_THEME,
    resolved: DEFAULT_THEME,

/**

* Set a specific theme.
  */
  setTheme: (theme) => {
  if (theme !== "dark" && theme !== "light") {
  return;
  }


try {



  localStorage.setItem(STORAGE_KEY, theme);
} catch {
  // Ignore storage errors while still applying the theme.
}

applyTheme(theme);

set({
  theme,
  resolved: theme,
});


},

/**

* Toggle between dark and light mode.
  */
  toggleTheme: () => {
  const currentTheme = get().theme;
  const nextTheme = currentTheme === "dark" ? "light" : "dark";


get().setTheme(nextTheme);


},

/**

* Kept for compatibility with existing components that may
* still call cycle().
*
* This now cycles only between light and dark.
  */
  cycle: () => {
  const currentTheme = get().theme;
  const nextTheme = currentTheme === "dark" ? "light" : "dark";


get().setTheme(nextTheme);


},
}));

/**

* Restore the user's saved theme when the client application loads.
  */
  function hydrateTheme() {
  const theme = readStoredTheme();

applyTheme(theme);

useThemeStore.setState({
theme,
resolved: theme,
});
}

export {
hydrateTheme,
useThemeStore,
};
