/**
 * Auth store using Zustand for client-side token management.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  expiresAt: number | null;
  user: {
    id: string;
    email: string;
    fullName: string | null;
  } | null;
  _hasHydrated: boolean;

  // Actions
  setTokens: (accessToken: string, refreshToken: string, expiresIn: number) => void;
  setUser: (user: AuthState["user"]) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
  isTokenExpired: () => boolean;
  setHasHydrated: (state: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      expiresAt: null,
      user: null,
      _hasHydrated: false,

      setHasHydrated: (state) => set({ _hasHydrated: state }),

      setTokens: (accessToken, refreshToken, expiresIn) => {
        const expiresAt = Date.now() + expiresIn * 1000;
        set({ accessToken, refreshToken, expiresAt });
        // Set a cookie for middleware to detect auth status
        if (typeof document !== "undefined") {
          const isSecure = window.location.protocol === "https:";
          const securePart = isSecure ? "; Secure" : "";
          document.cookie = `resume-crafter-auth=true; path=/; max-age=${expiresIn}; SameSite=Lax${securePart}`;
        }
      },

      setUser: (user) => set({ user }),

      logout: () => {
        set({
          accessToken: null,
          refreshToken: null,
          expiresAt: null,
          user: null,
        });
        // Remove the auth cookie
        if (typeof document !== "undefined") {
          const isSecure = window.location.protocol === "https:";
          const securePart = isSecure ? "; Secure" : "";
          document.cookie = `resume-crafter-auth=; path=/; max-age=0; SameSite=Lax${securePart}`;
        }
      },

      isAuthenticated: () => {
        const { accessToken, expiresAt } = get();
        if (!accessToken || !expiresAt) return false;
        return Date.now() < expiresAt;
      },

      isTokenExpired: () => {
        const { expiresAt } = get();
        if (!expiresAt) return true;
        // Consider expired if less than 1 minute remaining
        return Date.now() > expiresAt - 60000;
      },
    }),
    {
      name: "resume-crafter-auth",
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        expiresAt: state.expiresAt,
        user: state.user,
      }),
      onRehydrateStorage: () => (state, error) => {
        // Always set hydrated to true, even if state is undefined or there's an error
        if (state) {
          state.setHasHydrated(true);
        } else {
          // If state is undefined (no stored data), set hydrated via direct store access
          useAuthStore.setState({ _hasHydrated: true });
        }
      },
    }
  )
);
