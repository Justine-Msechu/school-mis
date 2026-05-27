import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "light" | "dark" | "blue";

export const THEMES: { key: Theme; label: string; preview: string }[] = [
  { key: "light", label: "Light",     preview: "#ffffff" },
  { key: "dark",  label: "Dark",      preview: "#1e2433" },
  { key: "blue",  label: "Ocean Blue",preview: "#0284c7" },
];

interface ThemeState {
  theme: Theme;
  setTheme: (t: Theme) => void;
}

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme);
  // Toggle Tailwind dark class for any dark: variants we use
  document.documentElement.classList.toggle("dark", theme === "dark");
}

// Apply on load before React renders (avoids flash)
const _stored = (() => {
  try { return (JSON.parse(localStorage.getItem("mis-theme") || "{}") as any)?.state?.theme as Theme; } catch { return null; }
})();
if (_stored) applyTheme(_stored);
else applyTheme("light");

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: _stored ?? "light",
      setTheme(t) {
        applyTheme(t);
        set({ theme: t });
      },
    }),
    {
      name: "mis-theme",
      skipHydration: true, // pre-read synchronously above; skip async re-hydration
    }
  )
);
