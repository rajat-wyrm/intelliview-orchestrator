import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx,jsx,js}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: { DEFAULT: "var(--bg)", panel: "var(--bg-panel)", card: "var(--bg-card)" },
        accent: { DEFAULT: "#6366f1", light: "#818cf8", dark: "#4f46e5" },
        success: "#10b981",
        warn: "#f59e0b",
        danger: "#ef4444",
        muted: "var(--muted)",
        border: "var(--border)",
        zinc: {
          50: "var(--zinc-50)",
          100: "var(--zinc-100)",
          200: "var(--zinc-200)",
          300: "var(--zinc-300)",
          400: "var(--zinc-400)",
          500: "var(--zinc-500)",
          600: "var(--zinc-600)",
          700: "var(--zinc-700)",
          800: "var(--zinc-800)",
          900: "var(--zinc-900)",
          950: "var(--zinc-950)",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
