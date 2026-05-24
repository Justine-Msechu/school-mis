import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "@/api/auth";

interface AuthState {
  isLoggedIn: boolean;
  user: User | null;
  token: string | null;
  login: (user: User, token: string) => void;
  logout: () => void;
  can: (permission: string) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      isLoggedIn: false,
      user: null,
      token: null,

      login(user, token) {
        sessionStorage.setItem("mis_token", token);
        localStorage.setItem("mis_token", token);
        set({ isLoggedIn: true, user, token });
      },

      logout() {
        sessionStorage.removeItem("mis_token");
        localStorage.removeItem("mis_token");
        set({ isLoggedIn: false, user: null, token: null });
      },

      can(permission: string) {
        const user = get().user;
        if (!user) return false;
        if (user.permissions.includes("*")) return true;
        return user.permissions.includes(permission);
      },
    }),
    {
      name: "mis-auth",
      partialize: (s) => ({ user: s.user, token: s.token }),
      onRehydrateStorage: () => (state) => {
        if (state?.token) {
          sessionStorage.setItem("mis_token", state.token);
          localStorage.setItem("mis_token", state.token);
          state.isLoggedIn = true;
        }
      },
    }
  )
);
