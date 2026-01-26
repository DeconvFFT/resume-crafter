/**
 * Theme store using Zustand for theme preference management.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

type ThemeMode = "light" | "dark" | "system";

interface ThemeState {
  mode: ThemeMode;
  _hasHydrated: boolean;

  // Actions
  setMode: (mode: ThemeMode) => void;
  toggleMode: () => void;
  setHasHydrated: (state: boolean) => void;
  getEffectiveTheme: () => "light" | "dark";
}

/**
 * Get the system's preferred color scheme
 */
const getSystemTheme = (): "light" | "dark" => {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
};

/**
 * Apply the theme class to the document element
 */
const applyTheme = (theme: "light" | "dark") => {
  if (typeof document === "undefined") return;

  const root = document.documentElement;
  if (theme === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
};

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      mode: "system",
      _hasHydrated: false,

      setHasHydrated: (state) => set({ _hasHydrated: state }),

      setMode: (mode) => {
        set({ mode });
        const effectiveTheme = mode === "system" ? getSystemTheme() : mode;
        applyTheme(effectiveTheme);
      },

      toggleMode: () => {
        const { mode } = get();
        // Cycle through: light -> dark -> system -> light
        const nextMode: ThemeMode =
          mode === "light" ? "dark" : mode === "dark" ? "system" : "light";
        get().setMode(nextMode);
      },

      getEffectiveTheme: () => {
        const { mode } = get();
        return mode === "system" ? getSystemTheme() : mode;
      },
    }),
    {
      name: "resume-crafter-theme",
      partialize: (state) => ({
        mode: state.mode,
      }),
      onRehydrateStorage: () => (state, error) => {
        if (state) {
          state.setHasHydrated(true);
          // Apply the theme after hydration
          const effectiveTheme =
            state.mode === "system" ? getSystemTheme() : state.mode;
          applyTheme(effectiveTheme);
        } else {
          useThemeStore.setState({ _hasHydrated: true });
        }
      },
    }
  )
);

/**
 * Initialize theme and set up system theme change listener
 * Should be called once on app mount
 */
export const initializeTheme = () => {
  const { mode, getEffectiveTheme } = useThemeStore.getState();

  // Apply initial theme
  applyTheme(getEffectiveTheme());

  // Listen for system theme changes when in "system" mode
  if (typeof window !== "undefined") {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

    const handleChange = () => {
      const currentMode = useThemeStore.getState().mode;
      if (currentMode === "system") {
        applyTheme(getSystemTheme());
      }
    };

    mediaQuery.addEventListener("change", handleChange);

    // Return cleanup function
    return () => mediaQuery.removeEventListener("change", handleChange);
  }

  return () => {};
};
