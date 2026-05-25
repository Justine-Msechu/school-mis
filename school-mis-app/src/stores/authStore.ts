import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "@/api/auth";

// Read persisted auth synchronously before React's first render.
const _readPersisted = (): { isLoggedIn: boolean; user: User | null; token: string | null; mustChangePw: boolean } => {
  try {
    const raw = localStorage.getItem("mis-auth");
    if (!raw) return { isLoggedIn: false, user: null, token: null, mustChangePw: false };
    const parsed = JSON.parse(raw) as { state?: { user?: User; token?: string; mustChangePw?: boolean } };
    const { user, token, mustChangePw } = parsed?.state ?? {};
    if (token && user) {
      sessionStorage.setItem("mis_token", token);
      return { isLoggedIn: true, user, token, mustChangePw: mustChangePw ?? false };
    }
  } catch { /* storage unavailable or corrupt */ }
  return { isLoggedIn: false, user: null, token: null, mustChangePw: false };
};

const _initial = _readPersisted();

interface AuthState {
  isLoggedIn:   boolean;
  user:         User | null;
  token:        string | null;
  mustChangePw: boolean;
  login:        (user: User, token: string, mustChangePw?: boolean) => void;
  logout:       () => void;
  setMustChangePw: (v: boolean) => void;
  can:          (permission: string) => boolean;
  refreshPermissions: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      isLoggedIn:   _initial.isLoggedIn,
      user:         _initial.user,
      token:        _initial.token,
      mustChangePw: _initial.mustChangePw,

      login(user, token, mustChangePw = false) {
        // Store token in sessionStorage only — cleared when browser tab closes.
        // localStorage is used only by Zustand persist for session restoration.
        sessionStorage.setItem("mis_token", token);
        set({ isLoggedIn: true, user, token, mustChangePw });
      },

      logout() {
        sessionStorage.removeItem("mis_token");
        localStorage.removeItem("mis-auth");
        set({ isLoggedIn: false, user: null, token: null, mustChangePw: false });
      },

      setMustChangePw(v: boolean) {
        set({ mustChangePw: v });
      },

      can(permission: string) {
        const user = get().user;
        if (!user) return false;
        if (user.permissions.includes("*")) return true;
        return user.permissions.includes(permission);
      },

      async refreshPermissions() {
        const { token, isLoggedIn } = get();
        if (!isLoggedIn || !token) return;
        try {
          const { default: api } = await import("@/api/client");
          const res = await api.get<User & { must_change_pw: boolean }>("/auth/me");
          const fresh = res.data;
          set((s) => ({
            user: s.user ? { ...s.user, permissions: fresh.permissions } : s.user,
            mustChangePw: fresh.must_change_pw,
          }));
        } catch {
          // 401 = token invalid (server restarted) → force logout
          get().logout();
        }
      },
    }),
    {
      name: "mis-auth",
      partialize: (s) => ({ user: s.user, token: s.token, mustChangePw: s.mustChangePw }),
    }
  )
);
