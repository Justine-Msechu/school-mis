import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "@/api/auth";

// Read persisted auth synchronously before React's first render.
// Zustand persist rehydrates asynchronously, so without this the
// store starts with isLoggedIn=false for one render, causing a
// login-page flash even for already-authenticated users.
const _readPersisted = (): { isLoggedIn: boolean; user: User | null; token: string | null } => {
  try {
    const raw = localStorage.getItem("mis-auth");
    if (!raw) return { isLoggedIn: false, user: null, token: null };
    const parsed = JSON.parse(raw) as { state?: { user?: User; token?: string } };
    const { user, token } = parsed?.state ?? {};
    if (token && user) {
      sessionStorage.setItem("mis_token", token);
      localStorage.setItem("mis_token", token);
      return { isLoggedIn: true, user, token };
    }
  } catch { /* storage unavailable or corrupt */ }
  return { isLoggedIn: false, user: null, token: null };
};

const _initial = _readPersisted();

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
      isLoggedIn: _initial.isLoggedIn,
      user: _initial.user,
      token: _initial.token,

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
    }
  )
);
